import { useEffect, useState } from 'react'
import { getHealth, createCodeReview, getCodeReviews } from '../services/api'
import CodeSubmitForm from '../components/CodeSubmitForm'
import ReviewList from '../components/ReviewList'
import ReviewDetail from '../components/ReviewDetail'

// No project management UI exists yet (that's a later stage), so every
// submission is attached to this fixed project for now.
const DEFAULT_PROJECT_ID = 1

function HomePage() {
  const [status, setStatus] = useState('checking...')
  const [reviews, setReviews] = useState([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [selectedReviewId, setSelectedReviewId] = useState(null)

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

      {selectedReview ? (
        <ReviewDetail review={selectedReview} onClose={() => setSelectedReviewId(null)} />
      ) : (
        <>
          <h2>Submit Code</h2>
          <CodeSubmitForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
          {error && <p className="error-message">{error}</p>}

          <h2>Submitted Reviews</h2>
          <ReviewList reviews={reviews} onSelectReview={setSelectedReviewId} />
        </>
      )}
    </div>
  )
}

export default HomePage
