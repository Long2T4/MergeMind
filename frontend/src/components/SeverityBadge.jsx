const SEVERITY_LABELS = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
}

function SeverityBadge({ severity }) {
  const label = SEVERITY_LABELS[severity] || severity

  return <span className={`severity-badge severity-${severity}`}>{label}</span>
}

export default SeverityBadge
