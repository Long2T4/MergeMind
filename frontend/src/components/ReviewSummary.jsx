const STATUS_LABELS = {
  completed: 'Completed',
  pending: 'Pending',
  failed: 'Failed',
}

function countBySeverity(issues, severity) {
  return issues.filter((issue) => issue.severity === severity).length
}

function ReviewSummary({ review }) {
  const { issues } = review
  const statusLabel = STATUS_LABELS[review.review_status] || review.review_status

  return (
    <div className="review-summary">
      <div className="review-summary-top">
        <span className={`status-pill status-${review.review_status}`}>{statusLabel}</span>
        <span className="review-summary-language">{review.programming_language}</span>
      </div>

      <div className="review-summary-count">
        <span className="review-summary-count-number">{issues.length}</span>
        <span className="review-summary-count-label">
          issue{issues.length === 1 ? '' : 's'} found
        </span>
      </div>

      <div className="severity-breakdown">
        <div className="severity-chip severity-chip-high">
          <span className="severity-chip-number">{countBySeverity(issues, 'high')}</span>
          <span className="severity-chip-label">High</span>
        </div>
        <div className="severity-chip severity-chip-medium">
          <span className="severity-chip-number">{countBySeverity(issues, 'medium')}</span>
          <span className="severity-chip-label">Medium</span>
        </div>
        <div className="severity-chip severity-chip-low">
          <span className="severity-chip-number">{countBySeverity(issues, 'low')}</span>
          <span className="severity-chip-label">Low</span>
        </div>
      </div>
    </div>
  )
}

export default ReviewSummary
