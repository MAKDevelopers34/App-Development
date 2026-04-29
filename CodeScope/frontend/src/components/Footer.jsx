import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer style={{
      background: 'var(--dark)',
      color: 'white',
      padding: '48px 0 24px',
      marginTop: '80px'
    }}>
      <div className="container">

        {/* Top section */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 1fr',
          gap: '40px',
          marginBottom: '40px'
        }}>

          {/* Brand */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <div style={{
                width: '32px', height: '32px',
                background: 'var(--primary)',
                borderRadius: '8px',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                  <rect x="3" y="3" width="14" height="14" rx="3" stroke="white" strokeWidth="1.5"/>
                  <path d="M7 8l2 2-2 2M11 12h2" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <span style={{ fontSize: '16px', fontWeight: '700' }}>
                Code<span style={{ color: 'var(--primary)' }}>Scope</span>
              </span>
            </div>
            <p style={{ fontSize: '13px', color: '#9aa0a6', lineHeight: '1.7', maxWidth: '280px' }}>
              AI-powered code complexity analyzer. Upload your code and get instant insights on time complexity, space complexity, and performance improvements.
            </p>
          </div>

          {/* Links */}
          <div>
            <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '14px', color: '#e8eaed' }}>
              Product
            </div>
            {['Home', 'Analyze', 'About'].map(item => (
              <Link
                key={item}
                to={item === 'Home' ? '/' : `/${item.toLowerCase()}`}
                style={{
                  display: 'block',
                  fontSize: '13px',
                  color: '#9aa0a6',
                  textDecoration: 'none',
                  marginBottom: '10px',
                  transition: 'color 0.2s'
                }}
              >
                {item}
              </Link>
            ))}
          </div>

          {/* Languages */}
          <div>
            <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '14px', color: '#e8eaed' }}>
              Supported Languages
            </div>
            {['Python', 'JavaScript', 'Java', 'C++', 'TypeScript'].map(lang => (
              <div key={lang} style={{
                fontSize: '13px',
                color: '#9aa0a6',
                marginBottom: '10px'
              }}>
                {lang}
              </div>
            ))}
          </div>

        </div>

        {/* Bottom */}
        <div style={{
          borderTop: '1px solid #3c4043',
          paddingTop: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ fontSize: '12px', color: '#9aa0a6' }}>
            © 2026 CodeScope. Built for algorithm analysis course project.
          </div>
          <div style={{ fontSize: '12px', color: '#9aa0a6' }}>
            Free & Open Source
          </div>
        </div>

      </div>
    </footer>
  );
}