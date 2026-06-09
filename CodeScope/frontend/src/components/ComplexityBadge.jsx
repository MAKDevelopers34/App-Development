const normalizeComplexity = (value = '') => String(value || '')
  .toLowerCase()
  .replace(/\s+/g, '')
  .replace(/\u00c2\u00b2/g, '^2')
  .replace(/\u00c2\u00b3/g, '^3')
  .replace(/\u00b2/g, '^2')
  .replace(/\u00b3/g, '^3')
  .replace(/\u00d7/g, '*')
  .replace(/\u03c6/g, 'phi')
  .replace(/\u00c2/g, '');

const classifyComplexity = (complexity = '') => {
  const normalized = normalizeComplexity(complexity);

  if (!normalized || normalized.includes('unknown')) {
    return {
      label: 'Estimate',
      style: { background: '#eef2f7', color: '#475569', border: '1px solid #cbd5e1' },
    };
  }

  const worstCaseRisk = normalized.includes('average') && normalized.includes('worst');
  const hasFactorial = normalized.includes('!') || normalized.includes('factorial');
  const hasExponential = /(\^n|2\*\*n|2\^n|3\^n|phi\^n)/.test(normalized);
  const hasCubic = /(\^3|n3|v3)/.test(normalized);
  const hasQuadratic = /(\^2|n2|v2|n\*n|v\*e|n\*w)/.test(normalized);
  const hasNLogN = /(nlog|n\*log|elog|\(v\+e\)log)/.test(normalized);
  const hasLinear = /(o\(n\)|\bn\b|v\+e|n\+m|n\+k|m\+n)/.test(normalized);
  const hasLog = normalized.includes('log') || normalized.includes('sqrt');

  if (hasFactorial || hasExponential || normalized.includes('ackermann')) {
    return {
      label: 'Critical',
      style: { background: '#fef2f2', color: '#b42318', border: '1px solid #fecaca' },
    };
  }

  if (hasCubic || worstCaseRisk) {
    return {
      label: 'High',
      style: { background: '#fff1f2', color: '#be123c', border: '1px solid #fecdd3' },
    };
  }

  if (hasQuadratic) {
    return {
      label: 'Costly',
      style: { background: '#fff7ed', color: '#c2410c', border: '1px solid #fed7aa' },
    };
  }

  if (hasNLogN) {
    return {
      label: 'Fair',
      style: { background: '#fffbeb', color: '#92400e', border: '1px solid #fde68a' },
    };
  }

  if (hasLinear) {
    return {
      label: 'Good',
      style: { background: '#ecfdf3', color: '#067647', border: '1px solid #bbf7d0' },
    };
  }

  if (normalized.includes('o(1)') || hasLog) {
    return {
      label: 'Great',
      style: { background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe' },
    };
  }

  return {
    label: '',
    style: { background: '#eef2f7', color: '#475569', border: '1px solid #cbd5e1' },
  };
};

export default function ComplexityBadge({ complexity }) {
  const rawValue = complexity || 'O(1)';
  const value = normalizeComplexity(rawValue).includes('unknown') ? 'O(1)' : rawValue;
  const { label, style } = classifyComplexity(value);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span style={{
        ...style,
        padding: '6px 14px',
        borderRadius: '20px',
        fontSize: '14px',
        fontWeight: '600',
        fontFamily: 'var(--font-code)'
      }}>
        {value}
      </span>
      {label && (
        <span style={{
          fontSize: '12px',
          color: 'var(--gray)',
          fontWeight: '500'
        }}>
          {label}
        </span>
      )}
    </div>
  );
}
