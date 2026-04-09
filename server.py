"""
Digital Asset Protection — Flask Backend API
==============================================
Exposes vhash.py and downloader.py as REST API endpoints
for the React frontend.

Endpoints:
  POST /api/register  — Upload video + org name → register
  POST /api/scan      — YouTube URL → download clips → piracy check
  GET  /api/registry  — List all registered assets
  GET  /api/scans     — Scan history

For the Google Solution Challenge — Digital Asset Protection
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import datetime
import shutil
import tempfile

from flask import Flask, request, jsonify
from flask_cors import CORS

from vhash import register_video
from downloader import scan_youtube_video

# ============================================================================
# APP SETUP
# ============================================================================

app = Flask(__name__)
CORS(app)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(BASE_DIR, "asset_registry.json")
SCAN_HISTORY_PATH = os.path.join(BASE_DIR, "scan_history.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================================
# HELPERS
# ============================================================================

def load_json(path):
    """Load a JSON file, returning empty list if it doesn't exist."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    """Save data as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ============================================================================
# ROUTES
# ============================================================================

@app.route("/api/register", methods=["POST"])
def api_register():
    """
    Register an original video asset.

    Accepts: multipart/form-data with:
      - file: the video file
      - organization: organization name (optional)

    Returns: registration record with SHA-256, frame count, timestamp
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    organization = request.form.get("organization", "Unknown")

    # Save uploaded file temporarily
    safe_name = file.filename.replace(" ", "_")
    temp_path = os.path.join(UPLOAD_DIR, safe_name)

    try:
        file.save(temp_path)
        print(f"\n[API] Registering '{safe_name}' for organization '{organization}'...")

        # Call vhash register_video()
        record = register_video(temp_path, db_path=REGISTRY_PATH)

        if record is None:
            return jsonify({"error": "Failed to process video"}), 500

        # Add organization to the record (update the registry)
        record["organization"] = organization

        # Update the registry with the organization field
        db = load_json(REGISTRY_PATH)
        if db:
            db[-1]["organization"] = organization
            save_json(REGISTRY_PATH, db)

        return jsonify({
            "success": True,
            "record": {
                "filename": record["filename"],
                "sha256": record["sha256"],
                "global_hash": record["global_hash"],
                "frame_count": record["frame_count"],
                "registered_at": record["registered_at"],
                "organization": organization,
            }
        }), 200

    except Exception as e:
        print(f"[API ERROR] Registration failed: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up uploaded file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """
    Scan a YouTube URL for piracy.

    Accepts: JSON with { "url": "https://youtube.com/..." }

    Returns: full verdict with per-clip breakdown
    """
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' field"}), 400

    url = data["url"].strip()
    if not url:
        return jsonify({"error": "URL cannot be empty"}), 400

    try:
        print(f"\n[API] Scanning URL: {url}")
        result = scan_youtube_video(url, db_path=REGISTRY_PATH)

        # Save to scan history
        scan_record = {
            "id": len(load_json(SCAN_HISTORY_PATH)) + 1,
            "url": url,
            "video_title": result.get("video_title"),
            "verdict": result["verdict"],
            "triggered_by": result.get("triggered_by"),
            "video_duration": result.get("video_duration"),
            "scanned_at": result.get("scanned_at"),
            "clips": result.get("clips", []),
            "matched_asset": None,
            "matched_registration": None,
        }

        # Extract match info from triggered clip
        if result.get("triggered_by"):
            for clip in result.get("clips", []):
                if f"clip_{clip['sample_number']}" == result["triggered_by"]:
                    scan_record["matched_asset"] = clip.get("matched_asset")
                    scan_record["matched_registration"] = clip.get("registration_timestamp")
                    break

        history = load_json(SCAN_HISTORY_PATH)
        history.append(scan_record)
        save_json(SCAN_HISTORY_PATH, history)

        return jsonify({"success": True, "result": result}), 200

    except Exception as e:
        print(f"[API ERROR] Scan failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/registry", methods=["GET"])
def api_registry():
    """Return all registered assets."""
    db = load_json(REGISTRY_PATH)
    return jsonify({"assets": db}), 200


@app.route("/api/registry/<sha256>", methods=["DELETE"])
def api_delete_registry(sha256):
    """Delete all registered assets matching a given SHA256."""
    db = load_json(REGISTRY_PATH)
    filtered = [a for a in db if a.get("sha256") != sha256]
    
    if len(filtered) == len(db):
        return jsonify({"success": False, "error": "Asset not found"}), 404
        
    save_json(REGISTRY_PATH, filtered)
    return jsonify({"success": True}), 200


@app.route("/api/scans", methods=["GET"])
def api_scans():
    """Return scan history."""
    history = load_json(SCAN_HISTORY_PATH)
    return jsonify({"scans": history}), 200


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Return summary statistics for the dashboard."""
    assets = load_json(REGISTRY_PATH)
    scans = load_json(SCAN_HISTORY_PATH)

    piracy_count = sum(1 for s in scans if s.get("verdict") == "PIRACY DETECTED")

    return jsonify({
        "total_assets": len(assets),
        "total_scans": len(scans),
        "piracy_detected": piracy_count,
        "original_content": len(scans) - piracy_count,
    }), 200


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("DIGITAL ASSET PROTECTION — API SERVER")
    print("=" * 60)
    print(f"  Registry: {REGISTRY_PATH}")
    print(f"  Scan History: {SCAN_HISTORY_PATH}")
    print(f"  Upload Dir: {UPLOAD_DIR}")
    print()

    app.run(debug=True, host="0.0.0.0", port=5000)
