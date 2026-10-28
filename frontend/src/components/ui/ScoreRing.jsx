// Circular 0–100 gauge used for the Stage 8 merge risk score and the
// dashboard completion rate.
function ScoreRing({ value, tone = 'accent', size = 112, stroke = 10, caption, display, label }) {
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const hasValue = value != null && Number.isFinite(Number(value))
  const clamped = hasValue ? Math.min(100, Math.max(0, Number(value))) : 0
  const offset = circumference * (1 - clamped / 100)

  return (
    <div className="score-ring" style={{ width: size, height: size }} role="img" aria-label={label}>
      <svg width={size} height={size} aria-hidden="true">
        <circle className="score-ring-track" cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} />
        <circle
          className={`score-ring-value ring-${hasValue ? tone : 'none'}`}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <span className="score-ring-label" aria-hidden="true">
        <span className="score-ring-number" style={{ fontSize: size * 0.27 }}>
          {display ?? (hasValue ? clamped : '—')}
        </span>
        {caption && <span className="score-ring-caption">{caption}</span>}
      </span>
    </div>
  )
}

export default ScoreRing
