// Compact high/medium/low bar plus a "4 (1H 2M 1L)" label.
function SeverityBar({ high = 0, medium = 0, low = 0, scale = 6, label }) {
  const total = high + medium + low
  const max = Math.max(scale, total, 1)
  const segments = [
    ['high', high],
    ['medium', medium],
    ['low', low],
  ].filter(([, count]) => count > 0)

  return (
    <span className="severity-bar">
      <span className="severity-bar-track" aria-hidden="true">
        {segments.map(([level, count]) => (
          <span
            key={level}
            className={`severity-bar-segment is-${level}`}
            style={{ width: `${(count / max) * 100}%` }}
          />
        ))}
      </span>
      <span className="severity-bar-label">
        {label ?? `${total} (${high}H ${medium}M ${low}L)`}
      </span>
    </span>
  )
}

export default SeverityBar
