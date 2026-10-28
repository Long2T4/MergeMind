// Stage 8 finding-based merge risk.
const RISK_CATEGORIES = [
  { key: 'security', label: 'Security' },
  { key: 'testing', label: 'Testing' },
  { key: 'maintainability', label: 'Maintainability' },
  { key: 'performance', label: 'Performance' },
]

// Returns { score, level } for a completed review with Stage 8 fields,
// otherwise null.
export function getRiskSummary(review) {
  const { risk_score, risk_level, risk_breakdown, review_status } = review
  if (review_status !== 'completed' || risk_score == null || !risk_breakdown) return null
  if (!Number.isFinite(Number(risk_score))) return null

  const score = Math.min(100, Math.max(0, Number(risk_score)))
  const level = ['low', 'medium', 'high'].includes(risk_level)
    ? risk_level
    : score >= 70
      ? 'high'
      : score >= 40
        ? 'medium'
        : 'low'
  return { score, level }
}

function RiskScoreCard({ review }) {
  const { risk_breakdown, review_status } = review

  // Failed or unfinished reviews do not have a completed risk assessment.
  if (review_status !== 'completed') {
    return (
      <section className="card risk-card">
        <h2 className="card-title">Overall Merge Risk</h2>
        <p className="risk-score-unavailable">
          Risk assessment unavailable because the review is not completed.
        </p>
      </section>
    )
  }

  const summary = getRiskSummary(review)

  // Older reviews may not contain Stage 8 risk fields.
  if (!summary) {
    return (
      <section className="card risk-card">
        <h2 className="card-title">Overall Merge Risk</h2>
        <p className="risk-score-unavailable">
          Risk assessment is not available for this review.
        </p>
      </section>
    )
  }

  const { score, level } = summary

  return (
    <section className="card risk-card" aria-labelledby="risk-card-title">
      <div className="risk-card-head">
        <div>
          <h2 id="risk-card-title" className="card-title">Overall Merge Risk</h2>
          <p className="card-meta">Finding-based risk assessment</p>
        </div>
        <div className="risk-score-overall">
          <strong>{score}/100</strong>
          <span className={`risk-level risk-level-${level}`}>{level.toUpperCase()} RISK</span>
        </div>
      </div>

      <div
        className="risk-track"
        role="progressbar"
        aria-label="Overall merge risk"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className={`risk-fill risk-fill-${level}`} style={{ width: `${score}%` }} />
      </div>

      <ul className="risk-categories">
        {RISK_CATEGORIES.map(({ key, label }) => {
          const rawValue = Number(risk_breakdown[key] ?? 0)
          const value = Number.isFinite(rawValue) ? Math.min(100, Math.max(0, rawValue)) : 0

          return (
            <li className="risk-category" key={key}>
              <div className="risk-category-label">
                <span>{label}</span>
                <span className="mono">{value}/100</span>
              </div>
              <div className="risk-category-track" aria-hidden="true">
                <div className="risk-category-fill" style={{ width: `${value}%` }} />
              </div>
            </li>
          )
        })}
      </ul>

      <p className="risk-note">
        This score reflects detected code review findings. It does not
        represent the probability of a failed merge or confirm that tests
        have passed.
      </p>
    </section>
  )
}

export default RiskScoreCard
