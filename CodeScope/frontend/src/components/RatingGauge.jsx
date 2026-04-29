export default function RatingGauge({ rating }) {
  const getColor = () => {
    if (rating >= 8) return '#34a853';
    if (rating >= 5) return '#fbbc04';
    return '#ea4335';
  };

  const getLabel = () => {
    if (rating >= 8) return 'Excellent';
    if (rating >= 5) return 'Good';
    return 'Needs Work';
  };

  const color = getColor();
  const percentage = (rating / 10) * 100;
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: '8px'
    }}>
      <div style={{ position: 'relative', width: '120px', height: '120px' }}>
        <svg width="120" height="120" viewBox="0 0 120 120">
          {/* Background circle */}
          <circle
            cx="60" cy="60" r="45"
            fill="none"
            stroke="#f1f3f4"
            strokeWidth="10"
          />
          {/* Progress circle */}
          <circle
            cx="60" cy="60" r="45"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            transform="rotate(-90 60 60)"
            style={{ transition: 'stroke-dashoffset 1s ease' }}
          />
        </svg>

        {/* Rating number in center */}
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center'
        }}>
          <div style={{
            fontSize: '28px',
            fontWeight: '700',
            color: color,
            lineHeight: '1'
          }}>
            {rating}
          </div>
          <div style={{
            fontSize: '11px',
            color: 'var(--gray)',
            marginTop: '2px'
          }}>
            /10
          </div>
        </div>
      </div>

      <div style={{
        fontSize: '14px',
        fontWeight: '600',
        color: color
      }}>
        {getLabel()}
      </div>
    </div>
  );
}