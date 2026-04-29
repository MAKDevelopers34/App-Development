import { Link, useLocation } from 'react-router-dom';
import '../styles/global.css';

export default function Navbar() {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <nav style={{
      background: 'white',
      borderBottom: '1px solid var(--border)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      boxShadow: 'var(--shadow)'
    }}>
      <div className="container" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '64px'
      }}>

        {/* Logo */}
        <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            background: 'var(--primary)',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="3" y="3" width="14" height="14" rx="3" stroke="white" strokeWidth="1.5"/>
              <path d="M7 8l2 2-2 2M11 12h2" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span style={{ fontSize: '18px', fontWeight: '700', color: 'var(--dark)' }}>
            Code<span style={{ color: 'var(--primary)' }}>Scope</span>
          </span>
        </Link>

        {/* Nav Links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {[
            { path: '/', label: 'Home' },
            { path: '/analyze', label: 'Analyze' },
            { path: '/about', label: 'About' },
          ].map(({ path, label }) => (
            <Link
              key={path}
              to={path}
              style={{
                textDecoration: 'none',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: '500',
                color: isActive(path) ? 'var(--primary)' : 'var(--gray)',
                background: isActive(path) ? 'var(--primary-light)' : 'transparent',
                transition: 'all 0.2s'
              }}
            >
              {label}
            </Link>
          ))}

          <Link to="/analyze" className="btn btn-primary" style={{ marginLeft: '8px' }}>
            Analyze Code
          </Link>
        </div>

      </div>
    </nav>
  );
}