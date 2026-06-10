import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container">

        <div className="footer-grid">
          <div>
            <div className="footer-brand-row">
              <div className="footer-brand-mark">
                <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                  <rect x="3" y="3" width="14" height="14" rx="3" stroke="white" strokeWidth="1.5"/>
                  <path d="M7 8l2 2-2 2M11 12h2" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <span className="footer-brand-name">
                Code<span style={{ color: 'var(--primary)' }}>Scope</span>
              </span>
            </div>
            <p className="footer-copy">
              Code complexity analysis for pasted snippets, ZIP projects, and GitHub repositories. Review Big-O results, hot code, and lower-complexity function rewrites.
            </p>
          </div>

          <div>
            <div className="footer-heading">
              Product
            </div>
            {['Home', 'Analyze', 'About'].map(item => (
              <Link
                key={item}
                to={item === 'Home' ? '/' : `/${item.toLowerCase()}`}
                className="footer-link"
              >
                {item}
              </Link>
            ))}
          </div>

          <div>
            <div className="footer-heading">
              Analysis Scope
            </div>
            {['File summary', 'Function complexity', 'Hot code', 'Modified functions', 'PDF reports'].map(item => (
              <div key={item} className="footer-scope">
                {item}
              </div>
            ))}
          </div>

        </div>

        <div className="footer-bottom">
          <div className="footer-legal">
            <span>Copyright 2026 CodeScope.</span>
            <span className="footer-made-by">
              Built by <strong>MAKDEVELOPERS</strong>
            </span>
          </div>
          <div className="footer-tagline">
            Time and space complexity reports
          </div>
        </div>

      </div>
    </footer>
  );
}
