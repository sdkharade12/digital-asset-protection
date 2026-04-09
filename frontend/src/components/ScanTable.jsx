import './ScanTable.css';

export default function ScanTable({ clips }) {
  if (!clips || clips.length === 0) {
    return (
      <div className="scan-table-wrapper">
        <div className="empty-message">No clip results to display</div>
      </div>
    );
  }

  return (
    <div className="scan-table-wrapper">
      <div className="scan-table-header">
        <h3>📋 Clip-by-Clip Analysis</h3>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Clip</th>
            <th>Timestamp</th>
            <th>Verdict</th>
            <th>Layer</th>
            <th>Layer Scores</th>
          </tr>
        </thead>
        <tbody>
          {clips.map((clip, idx) => {
            const isPiracy = clip.verdict === 'PIRACY DETECTED';
            const scores = clip.layer_scores || {};

            return (
              <tr key={idx}>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  Sample {clip.sample_number}
                </td>
                <td>
                  <span className="mono" style={{ fontSize: '0.82rem' }}>
                    {clip.timestamp_start}s — {clip.timestamp_end}s
                  </span>
                </td>
                <td>
                  <span className={`badge ${isPiracy ? 'badge-danger' : 'badge-success'}`}>
                    {isPiracy ? '🚨 PIRACY' : '✅ ORIGINAL'}
                  </span>
                </td>
                <td>
                  {clip.detection_layer
                    ? <span className="badge badge-warning">{clip.detection_layer}</span>
                    : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                </td>
                <td>
                  <div className="layer-scores">
                    {scores.L1_distance != null && (
                      <span className={`layer-score-tag ${clip.detection_layer === 'L1' ? 'matched' : ''}`}>
                        L1: {scores.L1_distance}
                      </span>
                    )}
                    {scores.L2a_coverage != null && (
                      <span className={`layer-score-tag ${clip.detection_layer === 'L2a' ? 'matched' : ''}`}>
                        L2a: {scores.L2a_coverage}%
                      </span>
                    )}
                    {scores.L2b_suspect_coverage != null && (
                      <span className={`layer-score-tag ${clip.detection_layer === 'L2b' ? 'matched' : ''}`}>
                        L2b: {scores.L2b_suspect_coverage}%
                      </span>
                    )}
                    {scores.L3_orb_ratio != null && (
                      <span className={`layer-score-tag ${clip.detection_layer === 'L3' ? 'matched' : ''}`}>
                        L3: {scores.L3_orb_ratio}%
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
