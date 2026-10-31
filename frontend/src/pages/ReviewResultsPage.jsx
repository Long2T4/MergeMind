import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import Icon from '../components/layout/Icon'
import ReviewDetail from '../components/ReviewDetail'
import ContextSummary from '../components/ContextSummary'
import EmptyState from '../components/ui/EmptyState'
import { projectLabel } from '../constants/projects'
import { useProjects } from '../hooks/useProjects'
import { getReviewHistoryDetail } from '../services/api'
import './pages.css'

function ResultsSkeleton() {
  return (
    <div className="results-skeleton" role="status" aria-label="Loading review...">
      <div className="skeleton" style={{ height: 172 }} />
      <div className="skeleton" style={{ height: 64 }} />
      <div className="skeleton" style={{ height: 64 }} />
    </div>
  )
}

// Loads a single review by id (GET /review-history/{id}), so a saved review
// opens correctly no matter where the user came from.
function ReviewResultsPage() {
  const { reviewId } = useParams()
  const location = useLocation()
  const { byId } = useProjects()
  const [review, setReview] = useState(null)
  const [error, setError] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const validId = /^\d+$/.test(reviewId) && Number(reviewId) > 0

  useEffect(() => {
    if (!validId) return undefined
    let active = true
    setReview(null)
    setError(null)
    getReviewHistoryDetail(reviewId)
      .then((data) => { if (active) setReview(data) })
      .catch((err) => {
        if (active) setError({ notFound: err.status === 404 })
      })
    return () => { active = false }
  }, [reviewId, attempt, validId])

  // Only follow in-app paths ("/..." but not "//host"), never external URLs.
  const from = location.state?.from
  const isInAppPath = typeof from === 'string' && /^\/(?!\/)/.test(from)
  const backTo = isInAppPath ? from : '/history'
  const backLabel = (isInAppPath && location.state?.fromLabel) || 'Back to history'

  let content
  if (!validId || error?.notFound) {
    content = (
      <div className="card">
        <EmptyState
          title={`Review #${reviewId} could not be found.`}
          action={<Link to="/history" className="btn btn-secondary btn-sm">Go to history</Link>}
        >
          It may have been removed.
        </EmptyState>
      </div>
    )
  } else if (error) {
    content = (
      <div className="notice notice-error" role="alert">
        <span>Could not load this review. Check the backend connection.</span>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAttempt((n) => n + 1)}>
          Try again
        </button>
      </div>
    )
  } else if (!review) {
    content = <ResultsSkeleton />
  } else {
    content = (
      <>
        <ContextSummary summary={location.state?.contextSummary} failed={review.review_status === 'failed'} />
        <ReviewDetail review={review} projectName={projectLabel(byId.get(review.project_id), review.project_id)} />
      </>
    )
  }

  return (
    <div className="results-page">
      <Link to={backTo} className="back-link">
        <Icon name="arrowLeft" size={16} />
        {backLabel}
      </Link>
      {content}
    </div>
  )
}

export default ReviewResultsPage
