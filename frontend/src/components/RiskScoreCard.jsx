
const RISK_CATEGORIES = [
  { key: 'security', label: 'Security' },
  { key: 'testing', label: 'Testing' },
  { key: 'maintainability', label: 'Maintainability' },
  { key: 'performance', label: 'Performance' },
]

function RiskScoreCard({ review }) {
  const { risk_score, risk_level, risk_breakdown, review_status } = review

  // Failed or unfinished reviews do not have a completed risk assessment.
  if (review_status !== 'completed') {
    return (
      <section className="risk-score-card">
        <h3>Overall Merge Risk</h3>
        <p className="risk-score-unavailable">
          Risk assessment unavailable because the review is not completed.
        </p>
      </section>
    )
  }

  // Older reviews may not contain Stage 8 risk fields.
  if (risk_score == null || !risk_breakdown) {
    return (
      <section className="risk-score-card">
        <h3>Overall Merge Risk</h3>
        <p className="risk-score-unavailable">
          Risk assessment is not available for this review.
        </p>
      </section>
    )
  }

  const score = Math.min(100, Math.max(0, Number(risk_score)))
  const level = ['low', 'medium', 'high'].includes(risk_level)
    ? risk_level
    : score >= 70
      ? 'high'
      : score >= 40
        ? 'medium'
        : 'low'

  return (
    <section className="risk-score-card">
      <div className="risk-score-header">
        <div>
          <h3>Overall Merge Risk</h3>
          <p>Finding-based risk assessment</p>
        </div>

        <div className="risk-score-overall">
          <strong>{score}/100</strong>
          <span className={`risk-score-level risk-score-level-${level}`}>
            {level.toUpperCase()} RISK
          </span>
        </div>
      </div>

      <div className="risk-score-main-track">
        <div
          className={`risk-score-main-fill risk-score-fill-${level}`}
          style={{ width: `${score}%` }}
        />
      </div>

      <div className="risk-score-categories">
        {RISK_CATEGORIES.map(({ key, label }) => {
          const rawValue = Number(risk_breakdown[key] ?? 0)
          const value = Number.isFinite(rawValue)
            ? Math.min(100, Math.max(0, rawValue))
            : 0

          return (
            <div className="risk-score-category" key={key}>
              <div className="risk-score-category-label">
                <span>{label}</span>
                <span>{value}/100</span>
              </div>
              <div className="risk-score-category-track">
                <div
                  className="risk-score-category-fill"
                  style={{ width: `${value}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      <p className="risk-score-note">
        This score reflects detected code review findings. It does not
        represent the probability of a failed merge or confirm that tests
        have passed.
      </p>
    </section>
  )
}

export default RiskScoreCard
