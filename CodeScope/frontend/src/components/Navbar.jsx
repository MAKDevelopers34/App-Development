import { Link, useLocation } from 'react-router-dom';
import '../styles/global.css';

export default function Navbar() {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="app-nav">
      <div className="container app-nav-inner">

        {/* Logo */}
        <Link to="/" className="brand-link">
          <div className="brand-mark">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="3" y="3" width="14" height="14" rx="3" stroke="white" strokeWidth="1.5"/>
              <path d="M7 8l2 2-2 2M11 12h2" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="brand-name">
            Code<span style={{ color: 'var(--primary)' }}>Scope</span>
          </span>
        </Link>

        {/* Nav Links */}
        <div className="app-nav-links">
          {[
            { path: '/', label: 'Home' },
            { path: '/analyze', label: 'Analyze' },
            { path: '/about', label: 'About' },
          ].map(({ path, label }) => (
            <Link
              key={path}
              to={path}
              className={`nav-link ${isActive(path) ? 'active' : ''}`}
            >
              {label}
            </Link>
          ))}

          <Link to="/analyze" className="btn btn-primary nav-cta">
            Analyze Code
          </Link>
        </div>

      </div>
    </nav>
  );
}
