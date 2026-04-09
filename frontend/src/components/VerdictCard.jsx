import './VerdictCard.css';

export default function VerdictCard({ result }) {
  if (!result) return null;

  const isPiracy = result.verdict === 'PIRACY DETECTED';
  const cardClass = isPiracy ? 'piracy' : 'original';

  // Find the triggered clip details
  const triggeredClip = isPiracy && result.triggered_by
    ? result.clips?.find(c => c.sample_number === result.triggered_by || `clip_${c.sample_number}` === result.triggered_by || result.clips[0] === c)
    : null;

  return (
    <div className={`verdict-card ${cardClass}`}>
      <div className="verdict-header">
        <div className="verdict-icon">
          {isPiracy ? '🚨' : '✅'}
        </div>
        <div>
          <div className="verdict-title">
            {isPiracy ? 'Piracy Detected' : 'Original Content'}
          </div>
          <div className="verdict-subtitle">
            {isPiracy
              ? 'This video contains content from a registered asset.'
              : 'No matching registered assets found. Content appears to be original.'}
          </div>
        </div>
      </div>

      {isPiracy && triggeredClip && (
        <div className="verdict-details">
          <div className="verdict-detail-item">
            <div className="verdict-detail-label">Matched Asset</div>
            <div className="verdict-detail-value">{triggeredClip.matched_asset}</div>
          </div>

          <div className="verdict-detail-item">
            <div className="verdict-detail-label">Registration Timestamp</div>
            <div className="verdict-detail-value mono">
              {triggeredClip.registration_timestamp
                ? new Date(triggeredClip.registration_timestamp).toLocaleString()
                : 'N/A'}
            </div>
          </div>

          <div className="verdict-detail-item">
            <div className="verdict-detail-label">Detection Layer</div>
            <div className="verdict-detail-value">{triggeredClip.detection_layer}</div>
          </div>

          <div className="verdict-detail-item">
            <div className="verdict-detail-label">Suspect Timestamp</div>
            <div className="verdict-detail-value">
              {triggeredClip.timestamp_start}s — {triggeredClip.timestamp_end}s
            </div>
          </div>

          <div className="verdict-detail-item">
            <div className="verdict-detail-label">Confidence</div>
            <div className="verdict-detail-value">{triggeredClip.confidence}%</div>
          </div>

          <div className="verdict-detail-item">
            <div className="verdict-detail-label">Reason</div>
            <div className="verdict-detail-value">{triggeredClip.detection_reason}</div>
          </div>
        </div>
      )}
    </div>
  );
}
