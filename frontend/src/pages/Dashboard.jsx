import { useState, useEffect } from 'react';
import './Dashboard.css';

const API_URL = 'http://localhost:5000/api';

export default function Dashboard() {
  const [stats, setStats] = useState({
    total_assets: 0,
    total_scans: 0,
    piracy_detected: 0,
    original_content: 0,
  });
  const [scans, setScans] = useState([]);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, scansRes, assetsRes] = await Promise.all([
        fetch(`${API_URL}/stats`),
        fetch(`${API_URL}/scans`),
        fetch(`${API_URL}/registry`),
      ]);

      const statsData = await statsRes.json();
      const scansData = await scansRes.json();
      const assetsData = await assetsRes.json();

      setStats(statsData);
      setScans(scansData.scans || []);
      setAssets(assetsData.assets || []);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAsset = async (sha256) => {
    if (!window.confirm('Are you sure you want to remove this asset? This cannot be undone.')) return;
    
    try {
      const res = await fetch(`${API_URL}/registry/${sha256}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchData(); // Refresh the data
      } else {
        alert('Failed to delete asset');
      }
    } catch (err) {
      console.error('Error deleting asset:', err);
      alert('Error deleting asset');
    }
  };

  return (
    <div className="page-container">
      <div className="page-header animate-fade-in-up">
        <h1>📊 Dashboard</h1>
        <p>Overview of your digital asset protection activity.</p>
      </div>

      {/* Stats Grid */}
      <div className="dashboard-top">
        <div className="glass-card stat-card blue animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
          <div className="stat-card-header">
            <div className="stat-icon">📁</div>
          </div>
          <div className="stat-value">{stats.total_assets}</div>
          <div className="stat-label">Registered Assets</div>
        </div>

        <div className="glass-card stat-card purple animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
          <div className="stat-card-header">
            <div className="stat-icon">🔍</div>
          </div>
          <div className="stat-value">{stats.total_scans}</div>
          <div className="stat-label">Total Scans</div>
        </div>

        <div className="glass-card stat-card red animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
          <div className="stat-card-header">
            <div className="stat-icon">🚨</div>
          </div>
          <div className="stat-value">{stats.piracy_detected}</div>
          <div className="stat-label">Piracy Detected</div>
        </div>

        <div className="glass-card stat-card green animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          <div className="stat-card-header">
            <div className="stat-icon">✅</div>
          </div>
          <div className="stat-value">{stats.original_content}</div>
          <div className="stat-label">Original Content</div>
        </div>
      </div>

      {/* Scan History */}
      <div className="history-card animate-fade-in-up" style={{ animationDelay: '0.25s' }}>
        <div className="history-header">
          <h2>🕒 Scan History</h2>
          <span className="badge badge-info">{scans.length} records</span>
        </div>

        {scans.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>URL / Title</th>
                <th>Verdict</th>
                <th>Matched Asset</th>
                <th>Scanned At</th>
              </tr>
            </thead>
            <tbody>
              {[...scans].reverse().map((scan, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {scan.id || scans.length - idx}
                  </td>
                  <td>
                    <div className="url-cell" title={scan.url}>
                      {scan.video_title || scan.url}
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${
                      scan.verdict === 'PIRACY DETECTED' ? 'badge-danger' :
                      scan.verdict === 'ORIGINAL CONTENT' ? 'badge-success' :
                      'badge-warning'
                    }`}>
                      {scan.verdict === 'PIRACY DETECTED' ? '🚨 PIRACY' :
                       scan.verdict === 'ORIGINAL CONTENT' ? '✅ ORIGINAL' :
                       '⚠️ ERROR'}
                    </span>
                  </td>
                  <td className="asset-cell">
                    {scan.matched_asset || '—'}
                  </td>
                  <td className="timestamp-cell">
                    {scan.scanned_at
                      ? new Date(scan.scanned_at).toLocaleString()
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty-history">
            <div className="empty-history-icon">📋</div>
            <p>{loading ? 'Loading...' : 'No scans yet. Start by scanning a YouTube URL.'}</p>
          </div>
        )}
      </div>

      {/* Registered Assets List */}
      <div className="history-card animate-fade-in-up" style={{ animationDelay: '0.3s', marginTop: '32px', marginBottom: '32px' }}>
        <div className="history-header">
          <h2>📁 Registered Assets</h2>
          <span className="badge badge-info">{assets.length} assets</span>
        </div>

        {assets.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>File Name</th>
                <th>Organization</th>
                <th>Global Hash</th>
                <th>Registered At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {[...assets].reverse().map((asset, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {assets.length - idx}
                  </td>
                  <td>
                    <div className="url-cell" title={asset.filename}>
                      {asset.filename}
                    </div>
                  </td>
                  <td>{asset.organization}</td>
                  <td>
                    <span className="badge badge-warning" style={{fontFamily: 'monospace'}}>
                      {asset.global_hash?.substring(0, 8)}...
                    </span>
                  </td>
                  <td className="timestamp-cell">
                    {asset.registered_at
                      ? new Date(asset.registered_at).toLocaleString()
                      : '—'}
                  </td>
                  <td>
                    <button 
                       className="btn btn-primary" 
                       style={{ padding: '4px 8px', fontSize: '0.75rem', backgroundColor: 'var(--danger)', borderColor: 'var(--danger)' }}
                       onClick={() => handleDeleteAsset(asset.sha256)}
                       title="Remove Asset"
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty-history">
            <div className="empty-history-icon">📜</div>
            <p>{loading ? 'Loading...' : 'No assets registered yet. Go to Register Asset.'}</p>
          </div>
        )}
      </div>
    </div>
  );
}
