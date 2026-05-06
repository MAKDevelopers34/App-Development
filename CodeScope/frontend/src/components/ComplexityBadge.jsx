export default function ComplexityBadge({ complexity }) {
  const getStyle = () => {
    const good = ['O(1)', 'O(log n)'];
    const medium = ['O(n)', 'O(n log n)'];
    if (good.includes(complexity)) {
      return { background: '#e6f4ea', color: '#34a853', border: '1px solid #34a853' };
    } else if (medium.includes(complexity)) {
      return { background: '#fef7e0', color: '#b06000', border: '1px solid #fbbc04' };
    } else {
      return { background: '#fce8e6', color: '#ea4335', border: '1px solid #ea4335' };
    }
  };

  const getLabel = () => {
    const labels = {
      'O(1)': 'Excellent',
      'O(log n)': 'Great',
      'O(n)': 'Good',
      'O(n log n)': 'Fair',
      'O((log n)!)': 'Critical',
      'O(n²)': 'Poor',
      'O(n³)': 'Critical'
    };
    return labels[complexity] || '';
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span style={{
        ...getStyle(),
        padding: '6px 14px',
        borderRadius: '20px',
        fontSize: '14px',
        fontWeight: '600',
        fontFamily: 'var(--font-code)'
      }}>
        {complexity}
      </span>
      <span style={{
        fontSize: '12px',
        color: 'var(--gray)',
        fontWeight: '500'
      }}>
        {getLabel()}
      </span>
    </div>
  );
}
