export default function IssueCard({ issue, hideSolution = false }) {
  const getSeverityStyle = (severity) => {
    switch (severity) {
      case 'high':
        return {
          background: '#fce8e6',
          border: '1px solid #f5c6c2',
          color: '#ea4335',
          icon: '🔴'
        };
      case 'medium':
        return {
          background: '#fef7e0',
          border: '1px solid #fde68a',
          color: '#b06000',
          icon: '🟡'
        };
      default:
        return {
          background: '#e6f4ea',
          border: '1px solid #b7dfbf',
          color: '#34a853',
          icon: '🟢'
        };
    }
  };

  const style = getSeverityStyle(issue.severity);
  const solution = issue.ai_solution;
  const hasSolution = Boolean(solution?.code) && !hideSolution;
  const formatCode = (code) => String(code || '').replace(/\r\n/g, '\n').replace(/\t/g, '  ').trim();
  const providerLabel = solution?.source_label || 'AI';

  return (
    <div style={{
      background: style.background,
      border: style.border,
      borderRadius: '10px',
      padding: '14px 16px',
      marginBottom: '10px',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '12px'
    }}>
      <span style={{ fontSize: '16px', marginTop: '1px' }}>{style.icon}</span>
      <div style={{ flex: 1 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '4px'
        }}>
          <span style={{
            fontSize: '11px',
            fontWeight: '700',
            color: style.color,
            textTransform: 'uppercase',
            letterSpacing: '0.05em'
          }}>
            {issue.severity} severity
          </span>
          <span style={{
            fontSize: '11px',
            color: 'var(--gray)',
            background: 'white',
            padding: '1px 8px',
            borderRadius: '10px',
            border: '1px solid var(--border)'
          }}>
            Line {issue.line}
          </span>
          <span style={{
            fontSize: '11px',
            color: 'var(--gray)',
            background: 'white',
            padding: '1px 8px',
            borderRadius: '10px',
            border: '1px solid var(--border)'
          }}>
            {issue.type}
          </span>
        </div>
        <p style={{
          fontSize: '13px',
          color: 'var(--dark)',
          lineHeight: '1.5',
          margin: 0
        }}>
          {issue.message}
        </p>
        {hasSolution && (
          <div style={{
            marginTop: '14px',
            background: 'white',
            border: '1px solid #b7dfbf',
            borderRadius: '8px',
            padding: '12px'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '10px',
              flexWrap: 'wrap',
              marginBottom: '8px'
            }}>
              <div>
                <div style={{
                  fontSize: '12px',
                  fontWeight: '700',
                  color: 'var(--success)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  marginBottom: '3px'
                }}>
                  {providerLabel} Verified Solution
                </div>
                <div style={{ fontSize: '13px', color: 'var(--dark)', fontWeight: '600' }}>
                  {solution.title || 'Lower-complexity rewrite'}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {solution.complexity_before && (
                  <span style={{
                    fontSize: '11px',
                    fontFamily: 'var(--font-code)',
                    color: 'var(--danger)',
                    background: '#fce8e6',
                    borderRadius: '999px',
                    padding: '3px 8px'
                  }}>
                    {solution.complexity_before}
                  </span>
                )}
                {solution.complexity_after && (
                  <span style={{
                    fontSize: '11px',
                    fontFamily: 'var(--font-code)',
                    color: 'var(--success)',
                    background: '#e6f4ea',
                    borderRadius: '999px',
                    padding: '3px 8px'
                  }}>
                    {solution.complexity_after}
                  </span>
                )}
              </div>
            </div>
            {solution.description && (
              <p style={{ fontSize: '12px', color: 'var(--gray)', lineHeight: '1.5', margin: '0 0 8px' }}>
                {solution.description}
              </p>
            )}
            <pre style={{
              background: '#111827',
              color: '#e5e7eb',
              padding: '12px',
              borderRadius: '8px',
              fontSize: '12px',
              overflowX: 'auto',
              lineHeight: '1.5',
              fontFamily: 'var(--font-code)',
              whiteSpace: 'pre',
              margin: 0
            }}>{formatCode(solution.code)}</pre>
            {solution.notes && (
              <p style={{ fontSize: '11px', color: 'var(--gray)', lineHeight: '1.5', margin: '8px 0 0' }}>
                {solution.notes}
              </p>
            )}
          </div>
        )}
        {!hasSolution && issue.ai_solution_status && (
          <div style={{
            marginTop: '10px',
            background: 'white',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '10px 12px',
            fontSize: '12px',
            color: 'var(--gray)',
            lineHeight: '1.5'
          }}>
            {issue.ai_solution_status}
          </div>
        )}
      </div>
    </div>
  );
}
