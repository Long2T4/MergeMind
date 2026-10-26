import { useEffect, useState } from 'react'
import { getReviewHistoryDetail } from '../services/api'
import ReviewDetail from './ReviewDetail'
import './ReviewHistory.css'

const BACK_LABEL = 'Back to Review History'

// Loads a single review by id, so opening it from History never depends on
// the separately loaded (and possibly stale) Submitted Reviews list.
function HistoryReviewDetail({ reviewId, onBack }) {
  const [review, setReview] = useState(null)
  const [error, setError] = useState(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    setReview(null)
    setError(null)
    getReviewHistoryDetail(reviewId)
      .then((data) => { if (active) setReview(data) })
      .catch((err) => {
        if (!active) return
        setError(err.status === 404
          ? { notFound: true, message: `Review #${reviewId} could not be found. It may have been removed.` }
          : { notFound: false, message: 'Could not load this review. Check the backend connection.' })
      })
    return () => { active = false }
  }, [reviewId, attempt])

  if (review) {
    return <ReviewDetail review={review} onClose={onBack} backLabel={BACK_LABEL} />
  }

  return (
    <div className="review-detail">
      <button type="button" className="review-detail-close" onClick={onBack}>
        ← {BACK_LABEL}
      </button>
      {error ? (
        <div className="history-message history-error" role="alert">
          <p>{error.message}</p>
          {!error.notFound && (
            <button type="button" className="history-retry" onClick={() => setAttempt((n) => n + 1)}>
              Try again
            </button>
          )}
        </div>
      ) : (
        <p className="history-message" role="status">Loading review...</p>
      )}
    </div>
  )
}

export default HistoryReviewDetail
