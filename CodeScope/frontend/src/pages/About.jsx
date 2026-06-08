export default function About() {
  const pipeline = [
    ['Parse', 'Detect language from filename and inspect functions, classes, loops, recursion, calls, and allocation patterns.'],
    ['Classify', 'Estimate Big-O time and space using analyzer rules, known algorithm patterns, and call-chain effects.'],
    ['Prioritize', 'Promote only the highest-complexity functions into hot code while keeping all functions in the full table.'],
    ['Verify', 'When requested, accept AI rewrites only when they target the same function and improve analyzer complexity.'],
  ];

  const scope = [
    ['Inputs', 'Pasted source, ZIP projects, and public GitHub repositories with selectable folders.'],
    ['Languages', 'Python, JavaScript, TypeScript, Java, C, and C++ source files.'],
    ['Limits', 'Repository analysis limits files and source size so the backend remains responsive.'],
    ['Reports', 'Overall complexity, function complexity, hot code, modified functions, and PDF export.'],
  ];

  const reference = [
    ['O(1)', 'Constant', 'Direct access or fixed-size work', 'Great'],
    ['O(log n)', 'Logarithmic', 'Binary search, heap adjustment, or halving loops', 'Great'],
    ['O(n)', 'Linear', 'Single pass over an input-sized collection', 'Good'],
    ['O(n log n)', 'Linearithmic', 'Efficient sorting, divide-and-conquer, or heap-based work', 'Fair'],
    ['O(n^2)', 'Quadratic', 'Pairwise nested scans over the same input', 'Costly'],
    ['O(2^n)', 'Exponential', 'Branching recursion without enough pruning or memoization', 'Critical'],
  ];

  return (
    <div className="page-shell">
      <div className="container">
        <header className="about-hero">
          <div>
            <div className="eyebrow">How CodeScope works</div>
            <h1>Complexity analysis built around functions, hotspots, and verified rewrites.</h1>
            <p>
              CodeScope is designed for practical code review. It explains how a file scales, which functions create the most cost, and whether a lower-complexity alternative is available for the same function.
            </p>
          </div>
          <div className="about-summary">
            {scope.map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </header>

        <section className="section-stack">
          <div className="section-heading align-left">
            <div className="eyebrow">Pipeline</div>
            <h2>From source code to a focused report.</h2>
            <p>Each result section maps to one job: summarize, locate cost, explain functions, then show verified modified functions when they exist.</p>
          </div>
          <div className="timeline-grid">
            {pipeline.map(([title, description], index) => (
              <div key={title} className="premium-card timeline-card">
                <div className="step-number">{String(index + 1).padStart(2, '0')}</div>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="section-stack">
          <div className="section-heading align-left">
            <div className="eyebrow">Report contract</div>
            <h2>What the interface promises to show.</h2>
          </div>
          <div className="scope-grid">
            {[
              ['Overall Big-O', 'File-level scalable time and scalable space are shown first, with total allocation only when it adds useful information.'],
              ['Function table', 'Every detected function keeps its own row with code, direct time, time with calls, and explanation.'],
              ['Hot code', 'Only the highest-complexity functions are promoted, so lower-cost functions do not crowd the hotspot area.'],
              ['Modified functions', 'Groq-generated alternatives are loaded on request and displayed below the matching function, not as a separate unrelated block.'],
            ].map(([title, text]) => (
              <div key={title} className="scope-card">
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="reference-panel">
          <div className="reference-header">
            <div>
              <div className="eyebrow">Big-O reference</div>
              <h2>How complexity labels are presented.</h2>
            </div>
            <p>Labels are comparison aids for the report; the Big-O notation remains the source of truth.</p>
          </div>
          <div className="table-wrap">
            <table className="reference-table">
              <thead>
                <tr>
                  {['Notation', 'Class', 'Common signal', 'Review label'].map(label => (
                    <th key={label}>{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {reference.map(([notation, name, example, rating]) => (
                  <tr key={notation}>
                    <td><code>{notation}</code></td>
                    <td>{name}</td>
                    <td>{example}</td>
                    <td><span className={`rating-pill rating-${rating.toLowerCase()}`}>{rating}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
