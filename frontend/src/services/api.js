import { authFetch } from '../stage12/auth'
// Central place for all backend API calls.
// Keeping this separate means components don't need to know the backend URL.
// Override with VITE_API_BASE_URL (e.g. for a deployed backend); defaults to the local API.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function getProjects() {
  const response = await authFetch(`${API_BASE_URL}/projects/`)
  if (!response.ok) {
    throw new Error(`Failed to load projects (status ${response.status})`)
  }
  return response.json()
}

export async function getHealth() {
  const response = await authFetch(`${API_BASE_URL}/health`)
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }
  return response.json()
}

export async function createCodeReview({ projectId, submittedCode, programmingLanguage, projectContext }) {
  const response = await authFetch(`${API_BASE_URL}/code-reviews/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      submitted_code: submittedCode,
      programming_language: programmingLanguage,
      ...(projectContext ? { project_context: projectContext } : {}),
    }),
  })
  if (!response.ok) {
    const error = new Error(`Failed to submit code review (status ${response.status})`)
    if (response.status === 422) {
      const data = await response.json().catch(() => null)
      error.message = typeof data?.detail === 'string'
        ? data.detail : 'Check the code size and project context fields, then try again.'
      error.validation = true
    } else if (response.status === 404) {
      error.message = 'The selected project no longer exists. Refresh the page and choose another project.'
      error.validation = true
    }
    throw error
  }
  return response.json()
}

// Stage 11: start a review of a public GitHub pull request. Returns the
// pending review (202); the files are reviewed in the background.
export async function createPullRequestReview({ projectId, prUrl, sourceRoot = '' }) {
  const response = await authFetch(`${API_BASE_URL}/pull-request-reviews/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, pr_url: prUrl, source_root: sourceRoot }),
  })
  if (!response.ok) {
    const error = new Error(`Failed to start the pull request review (status ${response.status})`)
    // 422 invalid or oversized, 404 missing/private or no project, 409 already
    // running or changed, 429 too many running, 503 GitHub unavailable or rate
    // limited: the server's explanation is user-facing.
    if ([404, 409, 422, 429, 503].includes(response.status)) {
      const data = await response.json().catch(() => null)
      if (typeof data?.detail === 'string') {
        error.message = data.detail
        error.validation = true
      }
    }
    throw error
  }
  return response.json()
}

export async function getCodeReviews() {
  const response = await authFetch(`${API_BASE_URL}/code-reviews/`)
  if (!response.ok) {
    throw new Error(`Failed to load code reviews (status ${response.status})`)
  }
  return response.json()
}


// Stage 6: history dashboard endpoints; uses the existing backend.
export async function getReviewHistory({ q = '', language = '', status = '', limit = 8, offset = 0 } = {}) {
  const params = new URLSearchParams({ q, language, status, limit: String(limit), offset: String(offset) })
  const response = await authFetch(`${API_BASE_URL}/review-history/?${params}`)
  if (!response.ok) throw new Error(`History request failed (${response.status})`)
  return response.json()
}

// Stats use the same filters as the list, so the totals match what is shown.
export async function getReviewHistoryStats({ q = '', language = '', status = '' } = {}) {
  const params = new URLSearchParams({ q, language, status })
  const response = await authFetch(`${API_BASE_URL}/review-history/stats?${params}`)
  if (!response.ok) throw new Error(`History stats failed (${response.status})`)
  return response.json()
}

// Full review (code + issues) for the detail view.
export async function getReviewHistoryDetail(reviewId) {
  const response = await authFetch(`${API_BASE_URL}/review-history/${encodeURIComponent(reviewId)}`)
  if (!response.ok) {
    const error = new Error(`Review request failed (${response.status})`)
    error.status = response.status
    throw error
  }
  return response.json()
}
