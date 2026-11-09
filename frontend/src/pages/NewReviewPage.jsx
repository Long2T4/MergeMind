import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import CodeSubmitForm from '../components/CodeSubmitForm'
import PullRequestForm from '../components/PullRequestForm'
import { LANGUAGES } from '../constants/languages'
import { useProjects } from '../hooks/useProjects'
import { createCodeReview, createPullRequestReview, getReviewHistoryDetail } from '../services/api'
import './pages.css'

const SOURCES = [
  { key: 'paste', label: 'Paste code' },
  { key: 'github', label: 'GitHub pull request' },
]

function NewReviewContent({ retryReviewId, retryPullRequest }) {
  const navigate = useNavigate()
  const { projects } = useProjects()
  const [source, setSource] = useState(retryPullRequest ? 'github' : 'paste')
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

  async function run(create) {
    setIsSubmitting(true)
    setError('')
    try {
      const review = await create()
      // The AI review can be slow; don't pull the user back if they've left.
      if (mounted.current) navigate(`/reviews/${review.id}`, { state: { contextSummary: review.context_summary } })
    } catch (err) {
      if (!mounted.current) return
      setError(err.validation ? err.message : 'Failed to submit code. Please try again.')
      setIsSubmitting(false)
    }
  }

  function handleSubmit({ code, language, projectId, projectContext }) {
    return run(() => createCodeReview({
      projectId,
      submittedCode: code,
      programmingLanguage: language,
      ...(projectContext ? { projectContext } : {}),
    }))
  }

  // Stage 11: the server checks the pull request, then reviews it in the
  // background; the results page shows progress.
  function handlePullRequestSubmit({ projectId, prUrl, sourceRoot }) {
    return run(() => createPullRequestReview({ projectId, prUrl, sourceRoot }))
  }

  function chooseSource(key) {
    if (isSubmitting) return
    setSource(key)
    setError('')
  }

  return (
    <div className="new-review">
      <div className="page-header">
        <div>
          <p className="breadcrumb">reviews / new</p>
          <h1 className="page-title">New review</h1>
          <p className="page-subtitle">
            {source === 'github'
              ? 'Paste a public GitHub pull request URL. MergeMind reviews the changed files, then explains every finding.'
              : "Paste code or upload a file. MergeMind's AI reviews it, then explains every finding."}
          </p>
        </div>
        <div className="segmented" role="group" aria-label="Review source">
          {SOURCES.map((item) => (
            <button
              key={item.key}
              type="button"
              aria-pressed={source === item.key}
              onClick={() => chooseSource(item.key)}
              disabled={isSubmitting && source !== item.key}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {source === 'github' ? (
        <>
          {retryPullRequest && (
            <p className="notice notice-info retry-notice" role="status">
              Retrying a pull request review. Running it reviews the pull request again as it is now; the original stays in your history.
            </p>
          )}
          <PullRequestForm
            projects={projects}
            initialValues={retryPullRequest || {}}
            onSubmit={handlePullRequestSubmit}
            isSubmitting={isSubmitting}
            error={error}
          />
        </>
      ) : (
        <>
          {retryReviewId && initialValues && !retryError && (
            <p className="notice notice-info retry-notice" role="status">
              Retrying review #{retryReviewId}. Running it creates a new review; the original stays in your history. If it used project context, attach those files again.
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
        </>
      )}
    </div>
  )
}

// Remount when the retry target changes (e.g. clicking "New Review" while
// retrying), so no stale prefill or error carries over.
function NewReviewPage() {
  const location = useLocation()
  const retryReviewId = location.state?.retryReviewId ?? null
  const retryPullRequest = location.state?.retryPullRequest ?? null
  const key = retryReviewId ?? (retryPullRequest ? `pr-${retryPullRequest.prUrl}` : 'new')
  return <NewReviewContent key={key} retryReviewId={retryReviewId} retryPullRequest={retryPullRequest} />
}

export default NewReviewPage
