import { Link } from 'react-router-dom';
import heroImage from '../assets/hero.png';

export default function Home() {
  const metrics = [
    ['Big-O Time', 'Scalable runtime'],
    ['Big-O Space', 'Memory growth'],
    ['Hot Code', 'Highest-cost functions'],
    ['AI Rewrites', 'Verified alternatives'],
  ];

  const workflow = [
    ['01', 'Add source', 'Paste code, upload a ZIP, or point CodeScope to a public GitHub repository.'],
    ['02', 'Choose scope', 'Select inputs or a repository folder so analysis stays focused on the right files.'],
    ['03', 'Review report', 'Inspect complexity, exact function snippets, hot code, and improved rewrites.'],
  ];

  const capabilities = [
    ['Complexity Engine', 'Time and space complexity', 'Detect Big-O behavior from loops, recursion, calls, built-ins, and allocation patterns.'],
    ['Function View', 'Every function in context', 'See direct function cost, cost with called functions, exact code snippets, and explanations.'],
    ['Hot Code', 'Focus where cost is highest', 'Only the maximum-complexity sections are promoted to the hot code area.'],
    ['Groq Rewrites', 'Lower-complexity alternatives', 'Request modified functions separately and show accepted rewrites below the matching function.'],
    ['Repository Scope', 'GitHub folder selection', 'Analyze the folder that matters instead of unrelated generated, vendor, or config files.'],
    ['PDF Reports', 'Clean exportable results', 'Download a polished report with summaries, function details, hotspots, and recommendations.'],
  ];

  const previewRows = [
    ['build_string()', 'O(n^2)', 'Costly'],
    ['has_duplicate()', 'O(n^2)', 'Costly'],
    ['binary_search()', 'O(log n)', 'Great'],
  ];

  return (
    <div>
      <section
        className="home-hero"
        style={{
          backgroundImage: `linear-gradient(90deg, rgba(15, 23, 42, 0.94), rgba(15, 23, 42, 0.7)), url(${heroImage})`,
        }}
      >
        <div className="container">
          <div className="hero-content">
            <div className="hero-eyebrow">Static complexity analysis for real code</div>
            <h1 className="hero-title">CodeScope</h1>
            <p className="hero-copy">
              A focused code complexity workspace for Big-O time, Big-O space, hot functions, and verified lower-complexity alternatives across pasted code, ZIP projects, and GitHub folders.
            </p>
            <div className="hero-actions">
              <Link to="/analyze" className="btn btn-large hero-primary">
                Analyze Code
              </Link>
              <Link to="/about" className="btn btn-large hero-secondary">
                View Method
              </Link>
            </div>
            <div className="hero-metrics">
              {metrics.map(([label, value]) => (
                <div key={label} className="hero-metric">
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="section-band white-band">
        <div className="container">
          <div className="workflow-grid">
            {workflow.map(([step, title, description]) => (
              <div key={step} className="workflow-step">
                <div className="step-number">{step}</div>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section-band">
        <div className="container report-preview-shell">
          <div className="section-copy">
            <div className="eyebrow">Result surface</div>
            <h2>See complexity the way engineers review code.</h2>
            <p>
              CodeScope separates the file summary, hot code, function-by-function complexity, and modified functions so the report stays useful even for large files.
            </p>
            <Link to="/analyze" className="btn btn-primary">
              Open Analyzer
            </Link>
          </div>
          <div className="report-preview" aria-label="CodeScope result preview">
            <div className="preview-header">
              <div>
                <span className="preview-label">CodeScope Complexity</span>
                <strong>sample.py</strong>
              </div>
              <div className="preview-score">8/10</div>
            </div>
            <div className="preview-metrics">
              <div>
                <span>Big O Time</span>
                <strong>O(n^2)</strong>
              </div>
              <div>
                <span>Big O Space</span>
                <strong>O(n)</strong>
              </div>
            </div>
            <div className="preview-table">
              {previewRows.map(([name, complexity, rating]) => (
                <div key={name} className="preview-row">
                  <code>{name}</code>
                  <span>{complexity}</span>
                  <b>{rating}</b>
                </div>
              ))}
            </div>
            <div className="preview-footer">Modified functions appear below matching functions after Groq verification.</div>
          </div>
        </div>
      </section>

      <section className="section-band white-band">
        <div className="container">
          <div className="section-heading">
            <div className="eyebrow">Analysis scope</div>
            <h2>Everything on the page is there for complexity review.</h2>
            <p>No generic filler. The interface is centered on the exact sections your tool is meant to deliver.</p>
          </div>
          <div className="feature-grid">
            {capabilities.map(([label, title, description]) => (
              <div key={title} className="premium-card feature-card">
                <span>{label}</span>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section-band">
        <div className="container">
          <div className="cta-band">
            <div>
              <div className="eyebrow">Ready for a real file</div>
              <h2>Analyze source, inspect hot code, then request modified functions only when needed.</h2>
            </div>
            <Link to="/analyze" className="btn btn-primary btn-large">
              Start Analysis
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
