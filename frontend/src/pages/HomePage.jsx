import { useEffect, useState } from 'react'
import { getHealth, createCodeReview, getCodeReviews } from '../services/api'
import CodeSubmitForm from '../components/CodeSubmitForm'
import ReviewList from '../components/ReviewList'
import ReviewDetail from '../components/ReviewDetail'
import ReviewHistory from '../components/ReviewHistory'
import HistoryReviewDetail from '../components/HistoryReviewDetail'

// No project management UI exists yet (that's a later stage), so every
// submission is attached to this fixed project for now.
const DEFAULT_PROJECT_ID = 1

const INITIAL_HISTORY_FILTERS = { search: '', language: '', status: '', page: 0 }

function HomePage() {
  const [status, setStatus] = useState('checking...')
  const [reviews, setReviews] = useState([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [selectedReviewId, setSelectedReviewId] = useState(null)
  const [showReviewHistory, setShowReviewHistory] = useState(false)
  // Kept here (not inside ReviewHistory) so filters and page survive opening a review.
  const [historyFilters, setHistoryFilters] = useState(INITIAL_HISTORY_FILTERS)
  const [historyReviewId, setHistoryReviewId] = useState(null)

  useEffect(() => {
    getHealth()
      .then((data) => setStatus(data.status))
      .catch(() => setStatus('backend unreachable'))

    loadReviews()
  }, [])

  function loadReviews() {
    getCodeReviews()
      .then(setReviews)
      .catch(() => setError('Could not load past reviews.'))
  }

  async function handleSubmit({ code, language }) {
    setIsSubmitting(true)
    setError('')
    try {
      await createCodeReview({
        projectId: DEFAULT_PROJECT_ID,
        submittedCode: code,
        programmingLanguage: language,
      })
      loadReviews()
    } catch (err) {
      setError('Failed to submit code. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const selectedReview = reviews.find((review) => review.id === selectedReviewId)

  return (
    <div className="home-page">
      <h1>MergeMind</h1>
      <p>Backend status: <strong>{status}</strong></p>

      {historyReviewId != null ? (
        <HistoryReviewDetail reviewId={historyReviewId} onBack={() => setHistoryReviewId(null)} />
      ) : selectedReview ? (
        <ReviewDetail review={selectedReview} onClose={() => setSelectedReviewId(null)} />
      ) : showReviewHistory ? (
        <ReviewHistory
          filters={historyFilters}
          onFiltersChange={setHistoryFilters}
          onSelectReview={setHistoryReviewId}
          onBack={() => setShowReviewHistory(false)}
        />
      ) : (
        <>
          <h2>Submit Code</h2>
          <CodeSubmitForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
          {error && <p className="error-message">{error}</p>}

          <h2>Submitted Reviews</h2>
          <button type="button" className="history-open-button" onClick={() => setShowReviewHistory(true)}>
            View Review History →
          </button>
          <ReviewList reviews={reviews} onSelectReview={setSelectedReviewId} />
        </>
      )}
    </div>
  )
}

export default HomePage
