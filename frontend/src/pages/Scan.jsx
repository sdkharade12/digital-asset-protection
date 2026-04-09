import { useState } from 'react';
import VerdictCard from '../components/VerdictCard';
import ScanTable from '../components/ScanTable';
import './Scan.css';

const API_URL = 'http://localhost:5000/api';

const SCAN_STEPS = [
  'Fetching video duration...',
  'Downloading clip 1...',
  'Analyzing clip 1...',
  'Downloading clip 2...',
  'Analyzing clip 2...',
  'Downloading clip 3...',
  'Analyzing clip 3...',
  'Generating verdict...',
];

export default function Scan() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(-1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleScan = async () => {
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentStep(0);

    // Simulate step progression while waiting for the API
    const stepInterval = setInterval(() => {
      setCurrentStep(prev => {
        if (prev < SCAN_STEPS.length - 2) return prev + 1;
        return prev;
      });
    }, 3500);

    try {
      const response = await fetch(`${API_URL}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });

      const data = await response.json();

      clearInterval(stepInterval);
      setCurrentStep(SCAN_STEPS.length - 1);

      // Brief pause to show final step
      setTimeout(() => {
        if (data.success) {
          setResult(data.result);
        } else {
          setError(data.error || 'Scan failed');
        }
        setLoading(false);
        setCurrentStep(-1);
      }, 600);
    } catch (err) {
      clearInterval(stepInterval);
      setError('Failed to connect to server. Is the backend running?');
      setLoading(false);
      setCurrentStep(-1);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !loading) handleScan();
  };

  return (
    <div className="page-container">
      <div className="page-header animate-fade-in-up">
        <h1>🔍 Scan for Piracy</h1>
        <p>Enter a YouTube URL to check if it contains pirated content from your registered assets.</p>
      </div>

      {/* URL Input */}
      <div className="glass-card scan-input-card animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        <div className="scan-input-row">
          <input
            id="youtube-url-input"
            type="url"
            className="input-field"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button
            id="scan-submit-btn"
            className="btn btn-primary"
            onClick={handleScan}
            disabled={loading || !url.trim()}
          >
            {loading ? (
              <>
                <span className="step-spinner" style={{ width: 14, height: 14 }}></span>
                Scanning...
              </>
            ) : (
              '🔍 Scan Video'
            )}
          </button>
        </div>
      </div>

      {/* Progress Steps */}
      {loading && currentStep >= 0 && (
        <div className="scan-progress">
          <div className="progress-steps">
            {SCAN_STEPS.map((step, idx) => {
              let status = 'pending';
              if (idx < currentStep) status = 'done';
              else if (idx === currentStep) status = 'active';

              return (
                <div className="progress-step" key={idx}>
                  <div className={`step-indicator ${status}`}>
                    {status === 'done' ? '✓' : status === 'active' ? (
                      <div className="step-spinner"></div>
                    ) : (idx + 1)}
                  </div>
                  <span className={`step-text ${status}`}>{step}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="glass-card animate-fade-in-up" style={{ padding: '20px 24px', maxWidth: 700, marginBottom: 24 }}>
          <span style={{ color: 'var(--danger)' }}>❌ {error}</span>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="scan-results">
          <VerdictCard result={result} />
          <div className="scan-results-gap"></div>
          <ScanTable clips={result.clips} />
        </div>
      )}
    </div>
  );
}
