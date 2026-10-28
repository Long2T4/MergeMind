import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import CodeSubmitForm from '../components/CodeSubmitForm'
import ComingSoon from '../components/ui/ComingSoon'
import { LANGUAGES } from '../constants/languages'
import { useProjects } from '../hooks/useProjects'
import { createCodeReview, getReviewHistoryDetail } from '../services/api'
import './pages.css'

function NewReviewContent({ retryReviewId }) {
  const navigate = useNavigate()
  const { projects } = useProjects()
  const [initialValues, setInitialValues] = useState(retryReviewId ? null : {})
  const [retryError, setRetryError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  // "Retry" from History or a failed review: prefill the original submission.
  useEffect(() => {
    if (!retryReviewId) return undefined
    let active = true
    getReviewHistoryDetail(retryReviewId)
      .then((review) => {
        if (!active) return
        setInitialValues({
          code: review.submitted_code,
          language: LANGUAGES.includes(review.programming_language) ? review.programming_language : 'other',
          projectId: review.project_id,
        })
      })
      .catch(() => {
        if (!active) return
        setRetryError(`Could not load review #${retryReviewId} to retry. You can paste the code instead.`)
        setInitialValues({})
      })
    return () => { active = false }
  }, [retryReviewId])

  async function handleSubmit({ code, language, projectId }) {
    setIsSubmitting(true)
    setError('')
    try {
      // Same request body as before the redesign: project_id, submitted_code, programming_language.
      const review = await createCodeReview({
        projectId,
        submittedCode: code,
        programmingLanguage: language,
      })
      // The AI review can be slow; don't pull the user back if they've left.
      if (mounted.current) navigate(`/reviews/${review.id}`)
    } catch {
      if (!mounted.current) return
      setError('Failed to submit code. Please try again.')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="new-review">
      <div className="page-header">
        <div>
          <p className="breadcrumb">reviews / new</p>
          <h1 className="page-title">New review</h1>
          <p className="page-subtitle">
            Paste code or upload a file. MergeMind&apos;s AI reviews it, then explains every finding.
          </p>
        </div>
        <div className="segmented" role="group" aria-label="Review source">
          <span className="segmented-item is-active">Paste code</span>
          <span className="segmented-item" aria-disabled="true">
            GitHub pull request <ComingSoon label="soon" />
          </span>
        </div>
      </div>

      {retryReviewId && initialValues && !retryError && (
        <p className="notice notice-info retry-notice" role="status">
          Retrying review #{retryReviewId}. Running it creates a new review; the original stays in your history.
        </p>
      )}
      {retryError && <p className="notice notice-error retry-notice" role="alert">{retryError}</p>}

      {initialValues === null ? (
        <p className="notice" role="status">Loading the original submission…</p>
      ) : (
        <CodeSubmitForm
          projects={projects}
          initialValues={initialValues}
          onSubmit={handleSubmit}
          isSubmitting={isSubmitting}
          error={error}
        />
      )}
    </div>
  )
}

// Remount when the retry target changes (e.g. clicking "New Review" while
// retrying), so no stale prefill or error carries over.
function NewReviewPage() {
  const location = useLocation()
  const retryReviewId = location.state?.retryReviewId ?? null
  return <NewReviewContent key={retryReviewId ?? 'new'} retryReviewId={retryReviewId} />
}

export default NewReviewPage
