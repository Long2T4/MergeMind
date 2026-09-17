function ReviewList({ reviews, onSelectReview }) {
  if (reviews.length === 0) {
    return <p className="review-list-empty">No code reviews submitted yet.</p>
  }

  return (
    <ul className="review-list">
      {reviews.map((review) => (
        <li key={review.id} className="review-list-item">
          <button
            type="button"
            className="review-list-item-button"
            onClick={() => onSelectReview(review.id)}
          >
            <div className="review-list-header">
              <span className="review-language">{review.programming_language}</span>
              <span className={`status-pill status-${review.review_status}`}>
                {review.review_status}
              </span>
            </div>
            <pre className="review-code-preview">{review.submitted_code}</pre>
            <span className="review-issue-count">
              {review.issues.length} issue{review.issues.length === 1 ? '' : 's'} found
            </span>
            <span className="review-date">
              {new Date(review.created_at).toLocaleString()}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

export default ReviewList
