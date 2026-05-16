import { Link } from 'react-router-dom';

export default function Home() {
  const features = [
    {
      icon: '⚡',
      title: 'Time Complexity',
      description: 'Instantly detects Big-O notation — O(1), O(n), O(n²) and more from your code structure.'
    },
    {
      icon: '💾',
      title: 'Space Complexity',
      description: 'Analyzes memory usage patterns and data structure allocations in your code.'
    },
    {
      icon: '📁',
      title: 'ZIP File Upload',
      description: 'Upload your entire project as a ZIP file and analyze all files at once.'
    },
    {
      icon: '🔗',
      title: 'GitHub Integration',
      description: 'Paste any public GitHub repository URL and analyze the entire codebase instantly.'
    },
    {
      icon: '🤖',
      title: 'Verified Grok Rewrites',
      description: 'Show optimized code only when Grok returns a same-behavior rewrite that CodeScope re-analyzes as lower complexity.'
    },
    {
      icon: '📄',
      title: 'PDF Reports',
      description: 'Download a professional PDF report with full analysis results and recommendations.'
    }
  ];

  const languages = ['Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C'];

  const steps = [
    { step: '01', title: 'Upload Your Code', description: 'Paste code, upload a ZIP file, or enter a GitHub URL' },
    { step: '02', title: 'Instant Analysis', description: 'Our engine analyzes complexity, detects issues and bottlenecks' },
    { step: '03', title: 'Get Results', description: 'View detailed reports, confidence notes, hotspots, and verified Grok rewrites when available' },
  ];

  return (
    <div>

      {/* Hero Section */}
      <section style={{
        background: 'linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%)',
        color: 'white',
        padding: '80px 0',
        textAlign: 'center'
      }}>
        <div className="container">
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(255,255,255,0.15)',
            padding: '6px 16px',
            borderRadius: '20px',
            fontSize: '13px',
            marginBottom: '24px'
          }}>
            🚀 Free & Open Source Code Analyzer
          </div>

          <h1 style={{
            fontSize: '52px',
            fontWeight: '800',
            lineHeight: '1.2',
            marginBottom: '20px',
            maxWidth: '700px',
            margin: '0 auto 20px'
          }}>
            Analyze Your Code's
            <span style={{ color: '#fbbf24' }}> Complexity</span> Instantly
          </h1>

          <p style={{
            fontSize: '18px',
            opacity: '0.9',
            maxWidth: '560px',
            margin: '0 auto 36px',
            lineHeight: '1.7'
          }}>
            Upload your code via ZIP, GitHub URL, or paste directly.
            Get instant Big-O analysis, performance rating, confidence notes, and verified Grok rewrites when available.
          </p>

          <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to="/analyze" className="btn btn-large" style={{
              background: 'white',
              color: 'var(--primary)',
              fontWeight: '600'
            }}>
              🔍 Start Analyzing — It's Free
            </Link>
            
            {/* Fixed: Added the missing <a tag */}
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="btn btn-large"
              style={{
                background: 'rgba(255,255,255,0.15)',
                color: 'white',
                border: '1.5px solid rgba(255,255,255,0.4)'
              }}
            >
              ⭐ Star on GitHub
            </a>
          </div>

          {/* Language badges */}
          <div style={{
            display: 'flex',
            gap: '10px',
            justifyContent: 'center',
            flexWrap: 'wrap',
            marginTop: '40px'
          }}>
            {languages.map(lang => (
              <span key={lang} style={{
                background: 'rgba(255,255,255,0.15)',
                padding: '4px 14px',
                borderRadius: '20px',
                fontSize: '13px',
                fontWeight: '500'
              }}>
                {lang}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section style={{ padding: '80px 0', background: 'white' }}>
        <div className="container" style={{ textAlign: 'center' }}>
          <h2 className="section-title">How It Works</h2>
          <p className="section-subtitle">Three simple steps to analyze your code</p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '32px',
            marginTop: '40px'
          }}>
            {steps.map(({ step, title, description }) => (
              <div key={step} style={{ textAlign: 'center' }}>
                <div style={{
                  width: '60px',
                  height: '60px',
                  background: 'var(--primary-light)',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px',
                  fontSize: '18px',
                  fontWeight: '700',
                  color: 'var(--primary)'
                }}>
                  {step}
                </div>
                <h3 style={{ fontSize: '17px', fontWeight: '600', marginBottom: '8px' }}>{title}</h3>
                <p style={{ fontSize: '14px', color: 'var(--gray)', lineHeight: '1.6' }}>{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section style={{ padding: '80px 0', background: 'var(--light-gray)' }}>
        <div className="container" style={{ textAlign: 'center' }}>
          <h2 className="section-title">Everything You Need</h2>
          <p className="section-subtitle">Powerful features to understand and improve your code</p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '20px',
            marginTop: '40px',
            textAlign: 'left'
          }}>
            {features.map(({ icon, title, description }) => (
              <div key={title} className="card" style={{ transition: 'transform 0.2s' }}
                onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-4px)'}
                onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
              >
                <div style={{ fontSize: '28px', marginBottom: '12px' }}>{icon}</div>
                <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>{title}</h3>
                <p style={{ fontSize: '13px', color: 'var(--gray)', lineHeight: '1.6' }}>{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{
        padding: '80px 0',
        background: 'var(--dark)',
        textAlign: 'center',
        color: 'white'
      }}>
        <div className="container">
          <h2 style={{ fontSize: '36px', fontWeight: '700', marginBottom: '16px' }}>
            Ready to Analyze Your Code?
          </h2>
          <p style={{ fontSize: '16px', opacity: '0.8', marginBottom: '32px' }}>
            Free forever. No signup required. Start analyzing in seconds.
          </p>
          <Link to="/analyze" className="btn btn-large" style={{
            background: 'var(--primary)',
            color: 'white',
            fontWeight: '600'
          }}>
            🔍 Analyze My Code Now
          </Link>
        </div>
      </section>

    </div>
  );
}
