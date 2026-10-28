import ReviewSummary from './ReviewSummary'
import IssueCard from './IssueCard'
import RiskScoreCard from './RiskScoreCard'

function ReviewDetail({ review, onClose, backLabel = 'Back to reviews' }) {
  return (
    <div className="review-detail">
      <button type="button" className="review-detail-close" onClick={onClose}>
        ← {backLabel}
      </button>

      <ReviewSummary review={review} />
      <RiskScoreCard review={review} />

      <pre className="review-detail-code">{review.submitted_code}</pre>

      {review.issues.length === 0 ? (
        <p className="review-detail-empty">
          {review.review_status === 'completed'
            ? 'No issues found — nice work!'
            : 'No issues to show for this review.'}
        </p>
      ) : (
        <ul className="issue-card-list">
          {review.issues.map((issue) => (
            <IssueCard key={issue.id} issue={issue} />
          ))}
        </ul>
      )}
    </div>
  )
}

export default ReviewDetail
