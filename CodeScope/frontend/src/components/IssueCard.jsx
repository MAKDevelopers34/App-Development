export default function IssueCard({ issue }) {
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
      </div>
    </div>
  );
}