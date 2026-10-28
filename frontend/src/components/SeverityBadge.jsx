const SEVERITY_LABELS = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
}

function SeverityBadge({ severity }) {
  const key = String(severity || '').toLowerCase()
  const label = SEVERITY_LABELS[key] || severity

  return <span className={`severity-badge severity-${key}`}>{label}</span>
}

export default SeverityBadge
