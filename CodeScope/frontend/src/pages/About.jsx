export default function About() {
  const algorithms = [
    {
      name: 'AST Traversal',
      complexity: 'O(n)',
      description: 'We parse your code into an Abstract Syntax Tree and traverse every node to detect loops, recursion, and data structures.'
    },
    {
      name: 'Depth First Search',
      complexity: 'O(V+E)',
      description: 'Used to traverse the call graph of your code and detect recursive function calls and their depth.'
    },
    {
      name: 'Pattern Matching',
      complexity: 'O(n)',
      description: 'Regex-based pattern matching scans for code smells, hardcoded values, global variables, and anti-patterns.'
    },
    {
      name: 'Weighted Scoring',
      complexity: 'O(1)',
      description: 'A weighted scoring algorithm combines complexity, issues, and patterns to produce a final performance rating from 1 to 10.'
    },
  ];

  const team = [
    { name: 'Algorithm Engine', description: 'Python + AST module for deep code analysis' },
    { name: 'REST API', description: 'Flask backend serving analysis results' },
    { name: 'Frontend', description: 'React + Vite for fast, modern UI' },
    { name: 'Mobile App', description: 'React Native + Expo for iOS and Android' },
    { name: 'PDF Reports', description: 'ReportLab for professional PDF generation' },
    { name: 'GitHub API', description: 'Fetch and analyze any public repository' },
  ];

  return (
    <div style={{ padding: '48px 0' }}>
      <div className="container" style={{ maxWidth: '900px' }}>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '56px' }}>
          <h1 className="section-title">About CodeScope</h1>
          <p className="section-subtitle" style={{ maxWidth: '600px', margin: '0 auto' }}>
            CodeScope is a free, open-source tool built as part of an Algorithm Analysis
            course project. It applies real algorithmic concepts to analyze and improve code quality.
          </p>
        </div>

        {/* Mission */}
        <div className="card" style={{ marginBottom: '32px', padding: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '12px' }}>
            🎯 Our Mission
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--gray)', lineHeight: '1.8' }}>
            Every developer writes code, but not everyone understands how efficient that code is.
            CodeScope makes algorithm analysis accessible to everyone — students, professionals,
            and teams. By uploading your code, you get instant feedback on time complexity,
            space complexity, confidence notes, and Grok-generated rewrites only when a verified lower-complexity alternative is available.
            All completely free.
          </p>
        </div>

        {/* Algorithms used */}
        <div style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px' }}>
            🧠 Algorithms We Use Internally
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))',
            gap: '16px'
          }}>
            {algorithms.map(({ name, complexity, description }) => (
              <div key={name} className="card" style={{ padding: '20px' }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '10px'
                }}>
                  <h3 style={{ fontSize: '15px', fontWeight: '600' }}>{name}</h3>
                  <span style={{
                    background: 'var(--primary-light)',
                    color: 'var(--primary)',
                    padding: '3px 10px',
                    borderRadius: '20px',
                    fontSize: '12px',
                    fontWeight: '600',
                    fontFamily: 'var(--font-code)'
                  }}>
                    {complexity}
                  </span>
                </div>
                <p style={{ fontSize: '13px', color: 'var(--gray)', lineHeight: '1.6' }}>
                  {description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Tech stack */}
        <div style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px' }}>
            🛠️ Tech Stack
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '12px'
          }}>
            {team.map(({ name, description }) => (
              <div key={name} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '14px',
                padding: '16px',
                background: 'white',
                border: '1px solid var(--border)',
                borderRadius: '10px'
              }}>
                <div style={{
                  width: '40px',
                  height: '40px',
                  background: 'var(--primary-light)',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '18px',
                  flexShrink: 0
                }}>
                  ⚙️
                </div>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '2px' }}>{name}</div>
                  <div style={{ fontSize: '12px', color: 'var(--gray)' }}>{description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Big-O Reference */}
        <div className="card" style={{ padding: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px' }}>
            📊 Big-O Complexity Reference
          </h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
              <thead>
                <tr style={{ background: 'var(--primary)', color: 'white' }}>
                  {['Notation', 'Name', 'Example', 'Rating'].map(h => (
                    <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontWeight: '600' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { notation: 'O(1)', name: 'Constant', example: 'Array index access', rating: '⭐⭐⭐⭐⭐', color: '#e6f4ea' },
                  { notation: 'O(log n)', name: 'Logarithmic', example: 'Binary search', rating: '⭐⭐⭐⭐⭐', color: '#e6f4ea' },
                  { notation: 'O(n)', name: 'Linear', example: 'Single loop', rating: '⭐⭐⭐⭐', color: '#fef7e0' },
                  { notation: 'O(n log n)', name: 'Linearithmic', example: 'Merge sort', rating: '⭐⭐⭐', color: '#fef7e0' },
                  { notation: 'O(n²)', name: 'Quadratic', example: 'Nested loops', rating: '⭐⭐', color: '#fce8e6' },
                  { notation: 'O(n³)', name: 'Cubic', example: 'Triple nested loops', rating: '⭐', color: '#fce8e6' },
                ].map(({ notation, name, example, rating, color }) => (
                  <tr key={notation} style={{ background: color, borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--font-code)', fontWeight: '600' }}>{notation}</td>
                    <td style={{ padding: '12px 16px' }}>{name}</td>
                    <td style={{ padding: '12px 16px', color: 'var(--gray)' }}>{example}</td>
                    <td style={{ padding: '12px 16px' }}>{rating}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
