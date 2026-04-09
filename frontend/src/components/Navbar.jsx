import { NavLink } from 'react-router-dom';
import './Navbar.css';

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <div className="navbar-brand-icon">⬡</div>
        <h2>Cyber Sentinel</h2>
        <span>Asset Protection</span>
      </div>

      <div className="navbar-nav">
        <NavLink
          to="/"
          end
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <span className="nav-icon">📊</span>
          Dashboard
        </NavLink>

        <NavLink
          to="/register"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <span className="nav-icon">📁</span>
          Register Asset
        </NavLink>

        <NavLink
          to="/scan"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <span className="nav-icon">🔍</span>
          Scan for Piracy
        </NavLink>
      </div>

      <div className="navbar-footer">
        <div className="navbar-footer-badge">
          <span className="navbar-footer-dot"></span>
          <span>SYSTEM ONLINE</span>
        </div>
      </div>
    </nav>
  );
}
