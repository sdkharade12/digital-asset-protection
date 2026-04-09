"""
Digital Asset Protection — Smart Video Downloader
==================================================
Downloads short clips from a YouTube URL at smart sample points,
then runs each clip through vhash.py's piracy detection pipeline.

Sampling strategy:
  - Skip first 20s (intro bumpers) and last 20s (outro)
  - Spread 3 sample points evenly across the remaining usable duration
  - Videos under 60s: just sample the middle
  - Each clip is 10 seconds long

For the Google Solution Challenge — Digital Asset Protection
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import shutil
import tempfile
import datetime
import imagehash

import yt_dlp

# Import vhash layer functions (do NOT modify vhash.py)
from vhash import (
    extract_frames,
    global_video_hash,
    compute_frame_hash_sequence,
    sliding_window_match,
    bag_of_hashes_match,
    orb_video_check,
)


# ============================================================================
# SMART SAMPLING — Calculate clip timestamps
# ============================================================================

def calculate_sample_points(duration, clip_length=10, skip_start=20, skip_end=20):
    """
    Calculate 3 smart sample timestamps spread across the usable portion
    of a video, skipping intro/outro bumpers.

    Args:
        duration    : Total video duration in seconds
        clip_length : How long each clip should be (default: 10s)
        skip_start  : Seconds to skip at the beginning
        skip_end    : Seconds to skip at the end

    Returns:
        List of (start_time, end_time) tuples for each clip
    """
    if duration <= 0:
        return []

    # Short videos (< 60s): just sample the middle
    if duration < 60:
        mid = max(0, (duration / 2) - (clip_length / 2))
        end = min(duration, mid + clip_length)
        return [(mid, end)]

    # Calculate usable range
    usable_start = skip_start
    usable_end = max(skip_start + clip_length, duration - skip_end)
    usable_duration = usable_end - usable_start

    if usable_duration < clip_length:
        # Video is too short after skipping — just sample the middle
        mid = max(0, (duration / 2) - (clip_length / 2))
        return [(mid, min(duration, mid + clip_length))]

    # Spread 3 sample points evenly across usable duration
    points = []
    for i in range(3):
        # Place at 1/6, 3/6, 5/6 of usable range (centered in thirds)
        fraction = (2 * i + 1) / 6
        start = usable_start + (usable_duration * fraction) - (clip_length / 2)
        start = max(usable_start, min(start, usable_end - clip_length))
        end = start + clip_length
        points.append((round(start, 1), round(end, 1)))

    return points


# ============================================================================
# VIDEO DURATION FETCH (without downloading the whole video)
# ============================================================================

def get_video_duration(url):
    """
    Fetch the total duration of a YouTube video without downloading it.

    Returns:
        duration (float) in seconds, or None on failure
        title (str) video title
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get('duration', 0)
            title = info.get('title', 'Unknown')
            print(f"  [INFO] Video: {title}")
            print(f"  [INFO] Duration: {duration}s")
            return duration, title
    except Exception as e:
        print(f"  [ERROR] Failed to fetch video info: {e}")
        return None, None


def download_full_video(url, output_path):
    """
    Download the entire video using yt-dlp (fallback for missing ffmpeg).
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'worst[ext=mp4]/worst',
        'outtmpl': output_path,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if os.path.exists(output_path):
            return True

        for cand_ext in ['.mp4', '.webm', '.mkv']:
            cand = output_path.rsplit('.', 1)[0] + cand_ext
            if os.path.exists(cand):
                os.rename(cand, output_path)
                return True
        print(f"  [ERROR] Full video file not found after download")
        return False
    except Exception as e:
        print(f"  [ERROR] Failed to download full video: {e}")
        return False

def extract_subclip(input_path, output_path, start_time, end_time):
    """
    Extract a subclip locally using OpenCV.
    """
    import cv2
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return False
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
    
    current_time = start_time
    while current_time <= end_time:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        current_time += 1.0 / fps
        
    cap.release()
    out.release()
    return True


# ============================================================================
# DETAILED REGISTRY CHECK (wraps vhash layer functions)
# ============================================================================

def check_against_registry_detailed(suspect_path, db_path="asset_registry.json"):
    """
    Check a suspect video clip against ALL registered originals,
    returning detailed layer scores for each comparison.

    This reimplements the matching loop from vhash.check_against_registry()
    but captures and returns all layer metrics instead of just printing them.

    Returns:
        dict with verdict, matched_asset info, detection_layer, and all scores
        or None if no match and returns scores of best candidate
    """
    if not os.path.exists(db_path):
        print("  [ERROR] No registry found.")
        return {
            "verdict": "ERROR",
            "reason": "No asset registry found",
            "layer_scores": {}
        }

    with open(db_path, "r") as f:
        db = json.load(f)

    if not db:
        return {
            "verdict": "ERROR",
            "reason": "Registry is empty",
            "layer_scores": {}
        }

    # Extract suspect frames and compute fingerprints once
    susp_frames = extract_frames(suspect_path)
    if not susp_frames:
        return {
            "verdict": "ERROR",
            "reason": "Could not extract frames from suspect clip",
            "layer_scores": {}
        }

    susp_seq = compute_frame_hash_sequence(susp_frames)
    susp_glob = global_video_hash(susp_frames)

    best_result = None
    best_score = -1

    for record in db:
        print(f"\n  -- vs '{record['filename']}' (registered {record['registered_at']}) --")

        orig_glob = imagehash.hex_to_hash(record["global_hash"])
        orig_seq = [imagehash.hex_to_hash(h) for h in record["frame_sequence"]]

        scores = {
            "L1_distance": None,
            "L2a_coverage": None,
            "L2a_position": None,
            "L2b_suspect_coverage": None,
            "L2b_original_coverage": None,
            "L3_orb_ratio": None,
        }

        # ── L1: Global hash ──
        dist = int(orig_glob - susp_glob) if susp_glob else 999
        scores["L1_distance"] = dist
        print(f"  [L1] Hash distance: {dist}")

        candidate_result = None

        if dist <= 20:
            candidate_result = _build_result(
                verdict="PIRACY DETECTED",
                record=record,
                layer="L1",
                reason=f"Near-identical copy (hash distance={dist})",
                confidence=max(0, 100 - dist * 3),
                scores=scores
            )

        # ── L2a: Sliding window ──
        window_cov, pos = sliding_window_match(orig_seq, susp_seq)
        window_cov = float(window_cov)
        pos = int(pos)
        scores["L2a_coverage"] = round(window_cov, 1)
        scores["L2a_position"] = pos

        if window_cov > 40 and not candidate_result:
            candidate_result = _build_result(
                verdict="PIRACY DETECTED",
                record=record,
                layer="L2a",
                reason=f"Unedited clip detected ({window_cov:.1f}% match at ~{pos}s)",
                confidence=round(window_cov, 1),
                scores=scores
            )

        # ── L2b: Bag of hashes ──
        s_cov, o_cov = bag_of_hashes_match(orig_seq, susp_seq)
        s_cov = float(s_cov)
        o_cov = float(o_cov)
        scores["L2b_suspect_coverage"] = round(s_cov, 1)
        scores["L2b_original_coverage"] = round(o_cov, 1)

        if (s_cov > 40 or o_cov > 60) and not candidate_result:
            trigger = f"suspect_cov={s_cov:.1f}%" if s_cov > 40 else f"orig_cov={o_cov:.1f}%"
            candidate_result = _build_result(
                verdict="PIRACY DETECTED",
                record=record,
                layer="L2b",
                reason=f"Edited/reordered clip ({trigger})",
                confidence=round(max(s_cov, o_cov), 1),
                scores=scores
            )

        # ── L3: ORB (only if weak signals) ──
        weak_signal = dist < 100 or window_cov > 15 or s_cov > 15
        if weak_signal and not candidate_result:
            print(f"  [L3] Weak signal — running ORB...")
            orb_ratio = float(orb_video_check(susp_frames, susp_frames))
            scores["L3_orb_ratio"] = round(orb_ratio * 100, 1)

            if orb_ratio > 0.15 or (dist < 80 and orb_ratio > 0.08):
                candidate_result = _build_result(
                    verdict="PIRACY DETECTED",
                    record=record,
                    layer="L3",
                    reason=f"Visual overlap (ORB={orb_ratio*100:.1f}%)",
                    confidence=round(orb_ratio * 100, 1),
                    scores=scores
                )
            # Combined weak signals
            elif s_cov > 20 and orb_ratio > 0.05:
                candidate_result = _build_result(
                    verdict="PIRACY DETECTED",
                    record=record,
                    layer="L2b+L3",
                    reason=f"Bag+ORB combo (bag={s_cov:.1f}%, ORB={orb_ratio*100:.1f}%)",
                    confidence=round((s_cov + orb_ratio * 100) / 2, 1),
                    scores=scores
                )
            elif window_cov > 20 and orb_ratio > 0.05:
                candidate_result = _build_result(
                    verdict="PIRACY DETECTED",
                    record=record,
                    layer="L2a+L3",
                    reason=f"Window+ORB combo (window={window_cov:.1f}%, ORB={orb_ratio*100:.1f}%)",
                    confidence=round((window_cov + orb_ratio * 100) / 2, 1),
                    scores=scores
                )

        if candidate_result:
            cand_conf = float(candidate_result.get("confidence", 0))
            if cand_conf > best_score:
                best_score = cand_conf
                best_result = candidate_result

        # Track best scoring candidate (even if no match)
        combined_score = max(s_cov, window_cov, 100 - dist)
        if combined_score > best_score and not candidate_result:
            best_score = combined_score
            best_result = {
                "verdict": "ORIGINAL CONTENT",
                "matched_asset": None,
                "matched_sha256": None,
                "registration_timestamp": None,
                "detection_layer": None,
                "detection_reason": "No significant match found",
                "confidence": 0,
                "layer_scores": scores
            }

    # No match found
    if best_result is None:
        best_result = {
            "verdict": "ORIGINAL CONTENT",
            "matched_asset": None,
            "matched_sha256": None,
            "registration_timestamp": None,
            "detection_layer": None,
            "detection_reason": "No significant match found",
            "confidence": 0,
            "layer_scores": {}
        }

    return best_result


def _build_result(verdict, record, layer, reason, confidence, scores):
    """Helper to build a structured result dict."""
    return {
        "verdict": verdict,
        "matched_asset": record["filename"],
        "matched_sha256": record["sha256"],
        "registration_timestamp": record["registered_at"],
        "detection_layer": layer,
        "detection_reason": reason,
        "confidence": confidence,
        "layer_scores": scores
    }


# ============================================================================
# MAIN SCAN PIPELINE
# ============================================================================

def scan_youtube_video(url, db_path="asset_registry.json"):
    """
    Full pipeline: YouTube URL → smart clips → piracy check → verdict.

    Steps:
        1. Fetch video duration (no download yet)
        2. Calculate 3 smart sample points
        3. Download 3 x 10s clips at lowest quality
        4. Run each clip through check_against_registry_detailed()
        5. If ANY clip matches → PIRACY DETECTED for the whole video
        6. Clean up temp files

    Returns:
        dict with full results including per-clip breakdown
    """
    print(f"\n{'='*60}")
    print(f"SCANNING: {url}")
    print(f"{'='*60}")

    result = {
        "url": url,
        "verdict": "ORIGINAL CONTENT",
        "clips": [],
        "triggered_by": None,
        "video_duration": None,
        "video_title": None,
        "scanned_at": datetime.datetime.utcnow().isoformat() + "Z",
        "error": None,
    }

    # Step 1: Get video duration
    print("\n[Step 1] Fetching video duration...")
    duration, title = get_video_duration(url)
    if duration is None:
        result["verdict"] = "ERROR"
        result["error"] = "Failed to fetch video info"
        return result

    result["video_duration"] = duration
    result["video_title"] = title

    temp_dir = tempfile.mkdtemp(prefix="dap_clips_")
    print(f"  Temp directory: {temp_dir}")

    try:
        full_video_path = os.path.join(temp_dir, "full_video.mp4")
        print("\n[Step 2] Downloading full video...")
        if not download_full_video(url, full_video_path):
            result["verdict"] = "ERROR"
            result["error"] = "Failed to download full video"
            shutil.rmtree(temp_dir, ignore_errors=True)
            return result

        print(f"\n[Step 3] Analyzing full video...")
        analysis = check_against_registry_detailed(full_video_path, db_path)

        clip_result = {
            "sample_number": "Full Scan",
            "timestamp_start": 0,
            "timestamp_end": duration,
            "verdict": analysis["verdict"],
            "matched_asset": analysis.get("matched_asset"),
            "matched_sha256": analysis.get("matched_sha256"),
            "registration_timestamp": analysis.get("registration_timestamp"),
            "detection_layer": analysis.get("detection_layer"),
            "detection_reason": analysis.get("detection_reason"),
            "confidence": analysis.get("confidence", 0),
            "layer_scores": analysis.get("layer_scores", {}),
        }

        if analysis["verdict"] == "PIRACY DETECTED":
            result["verdict"] = "PIRACY DETECTED"
            result["triggered_by"] = "Full Scan"

        result["clips"].append(clip_result)

    finally:
        # Clean up temp files
        print(f"\n[Cleanup] Removing temp directory...")
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Final verdict
    print(f"\n{'='*60}")
    print(f"FINAL VERDICT: {result['verdict']}")
    if result['triggered_by']:
        triggered_clip = result['clips'][0]
        if triggered_clip:
            print(f"  Triggered by: {triggered_clip['sample_number']} "
                  f"({triggered_clip['timestamp_start']}s - {triggered_clip['timestamp_end']}s)")
            print(f"  Matched asset: {triggered_clip['matched_asset']}")
            print(f"  Detection layer: {triggered_clip['detection_layer']}")
            print(f"  Reason: {triggered_clip['detection_reason']}")
    print(f"{'='*60}")

    return result


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Smart YouTube video piracy scanner")
    parser.add_argument("url", help="YouTube URL to scan")
    parser.add_argument("--db", default="asset_registry.json", help="Path to asset registry")
    args = parser.parse_args()

    result = scan_youtube_video(args.url, args.db)

    print("\n\n--- RAW RESULT ---")
    print(json.dumps(result, indent=2, default=str))
