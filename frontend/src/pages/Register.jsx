import { useState, useRef } from 'react';
import './Register.css';

const API_URL = 'http://localhost:5000/api';

export default function Register() {
  const [file, setFile] = useState(null);
  const [orgName, setOrgName] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => setDragging(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith('video/')) {
      setFile(droppedFile);
      setResult(null);
      setError(null);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setResult(null);
      setError(null);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('organization', orgName || 'Unknown');

      const response = await fetch(`${API_URL}/register`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        setResult(data.record);
      } else {
        setError(data.error || 'Registration failed');
      }
    } catch (err) {
      setError('Failed to connect to server. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header animate-fade-in-up">
        <h1>📁 Register Asset</h1>
        <p>Register your original video to establish proof of ownership with a cryptographic timestamp.</p>
      </div>

      <div className="register-grid">
        {/* Left: Upload Form */}
        <div className="glass-card upload-zone animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
          <div
            className={`upload-dropzone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
              id="video-upload-input"
            />

            <div className="upload-icon">{file ? '✅' : '📤'}</div>
            <div className="upload-text">
              {file ? 'File Selected' : 'Drop your video here or click to browse'}
            </div>
            <div className="upload-subtext">
              {file ? '' : 'Supports MP4, AVI, MKV, MOV'}
            </div>

            {file && (
              <div className="upload-filename">{file.name}</div>
            )}
          </div>

          <div className="form-section">
            <label className="form-label" htmlFor="org-name-input">Organization Name</label>
            <input
              id="org-name-input"
              type="text"
              className="input-field"
              placeholder="e.g., IPL Media Rights Holder"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
            />
          </div>

          <div className="register-btn-wrapper">
            <button
              id="register-submit-btn"
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={!file || loading}
              style={{ width: '100%' }}
            >
              {loading ? 'Processing...' : '🛡️ Register & Fingerprint'}
            </button>

            {loading && (
              <div className="register-progress">
                <div className="register-spinner"></div>
                Extracting frames, computing perceptual hashes...
              </div>
            )}

            {error && (
              <div style={{ marginTop: 12, color: 'var(--danger)', fontSize: '0.85rem' }}>
                ❌ {error}
              </div>
            )}
          </div>
        </div>

        {/* Right: Certificate */}
        <div className="certificate-wrapper animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          {result ? (
            <div className="certificate">
              <div className="certificate-inner">
                <div className="certificate-badge">🛡️ Certificate of Registration</div>

                <div className="certificate-title">{result.filename}</div>

                <div className="certificate-field">
                  <div className="certificate-field-label">Organization</div>
                  <div className="certificate-field-value">{result.organization}</div>
                </div>

                <div className="certificate-field">
                  <div className="certificate-field-label">SHA-256 Fingerprint</div>
                  <div className="certificate-field-value hash">
                    {result.sha256?.substring(0, 16)}...
                  </div>
                </div>

                <div className="certificate-field">
                  <div className="certificate-field-label">Frames Fingerprinted</div>
                  <div className="certificate-field-value">{result.frame_count} frames</div>
                </div>

                <hr className="certificate-divider" />

                <div className="certificate-field">
                  <div className="certificate-field-label">Registration Timestamp (UTC)</div>
                  <div className="certificate-timestamp">
                    🕐 {new Date(result.registered_at).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="certificate-empty">
              <div className="certificate-empty-icon">📜</div>
              <p>Register a video to see your<br />Certificate of Registration here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
