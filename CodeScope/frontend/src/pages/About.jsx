export default function About() {
  const pipeline = [
    ['01', 'Parse source', 'Language, functions, classes, callbacks, loops, recursion, calls, and allocation signals are separated before scoring.'],
    ['02', 'Build cost model', 'Direct function cost, cost with calls, space growth, and file-level behavior are compared with the same Big-O scale.'],
    ['03', 'Promote hotspots', 'Only the highest-cost functions move into Hot Code, while the full function table keeps the complete context.'],
    ['04', 'Verify rewrites', 'AI rewrites are accepted only when they target the same function and improve the analyzer complexity.'],
  ];

  const principles = [
    ['Function first', 'Every detected function keeps its own row, exact code snippet, direct time, time with calls, and space result.'],
    ['Project aware', 'ZIP and GitHub reports compare files without mixing time and space, then surface the worst project cost.'],
    ['No hidden rewrite block', 'Modified functions are attached below the matching original function, including hot-code functions.'],
  ];

  const reference = [
    ['O(1)', 'Constant', 'Direct access or fixed-size work', 'Great'],
    ['O(log n)', 'Logarithmic', 'Binary search, heap adjustment, or halving loops', 'Great'],
    ['O(n)', 'Linear', 'Single pass over an input-sized collection', 'Good'],
    ['O(n log n)', 'Linearithmic', 'Efficient sorting, divide-and-conquer, or heap-based work', 'Fair'],
    ['O(n^2)', 'Quadratic', 'Pairwise nested scans over the same input', 'Costly'],
    ['O(2^n)', 'Exponential', 'Branching recursion without enough pruning or memoization', 'Critical'],
  ];

  const reportCards = [
    ['Overall', 'Big-O time, Big-O space, rating, files, lines, and project-wide worst cases.'],
    ['Functions', 'Direct complexity, effective complexity, space, explanation, calls, and exact function code.'],
    ['Hot Code', 'Only the maximum-complexity function group, so the expensive code is easy to inspect.'],
    ['Modified', 'Lower-complexity alternatives requested from Groq and placed below their source function.'],
  ];

  return (
    <div className="page-shell about-page">
      <div className="container">
        <header className="about-premium-hero">
          <div className="about-hero-copy">
            <div className="eyebrow">CodeScope method</div>
            <h1>Complexity reporting built for serious code review.</h1>
            <p>
              CodeScope turns pasted code, ZIP projects, and GitHub folders into a structured complexity report with file summaries, function-level Big-O, hot code, and verified lower-complexity rewrites.
            </p>
          </div>
          <div className="about-command-panel" aria-label="CodeScope report model">
            <div className="command-topbar">
              <span />
              <span />
              <span />
            </div>
            <div className="command-line">
              <span>codescope</span> analyze --scope functions --report pdf
            </div>
            <div className="command-grid">
              {[
                ['Time', 'O(n log n)'],
                ['Space', 'O(n)'],
                ['Hotspots', '3'],
                ['Rewrites', 'On request'],
              ].map(([label, value]) => (
                <div key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          </div>
        </header>

        <section className="about-method-section">
          <div className="method-heading">
            <div>
              <div className="eyebrow">Pipeline</div>
              <h2>From source to final report.</h2>
            </div>
            <p>
              The analyzer keeps each layer separate so project summaries, file cards, hot code, function rows, and AI rewrites do not conflict.
            </p>
          </div>
          <div className="method-board">
            {pipeline.map(([step, title, description]) => (
              <div key={step} className="method-card">
                <span>{step}</span>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="about-proof-grid">
          <div className="proof-panel dark-proof">
            <div className="eyebrow">Report contract</div>
            <h2>Every section has one job.</h2>
            <p>
              The interface avoids generic result noise. It focuses on the core CodeScope promise: complexity by file, complexity by function, the hottest code, and modified functions when a lower-complexity rewrite is accepted.
            </p>
          </div>
          <div className="proof-list">
            {principles.map(([title, text]) => (
              <div key={title} className="proof-item">
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="report-contract-panel">
          <div className="reference-header compact-reference-header">
            <div>
              <div className="eyebrow">Result structure</div>
              <h2>What a CodeScope report contains.</h2>
            </div>
            <p>The same structure is used for pasted code, ZIP uploads, and selected GitHub folders.</p>
          </div>
          <div className="report-card-grid">
            {reportCards.map(([title, text]) => (
              <div key={title} className="report-contract-card">
                <span>{title}</span>
                <p>{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="reference-panel premium-reference">
          <div className="reference-header">
            <div>
              <div className="eyebrow">Big-O reference</div>
              <h2>Complexity labels used in reports.</h2>
            </div>
            <p>Labels help scanning, but the Big-O notation remains the source of truth.</p>
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
