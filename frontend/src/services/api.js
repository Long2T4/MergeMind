// Central place for all backend API calls.
// Keeping this separate means components don't need to know the backend URL.
// Override with VITE_API_BASE_URL (e.g. for a deployed backend); defaults to the local API.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function getProjects() {
  const response = await fetch(`${API_BASE_URL}/projects/`)
  if (!response.ok) {
    throw new Error(`Failed to load projects (status ${response.status})`)
  }
  return response.json()
}

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }
  return response.json()
}

export async function createCodeReview({ projectId, submittedCode, programmingLanguage }) {
  const response = await fetch(`${API_BASE_URL}/code-reviews/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      submitted_code: submittedCode,
      programming_language: programmingLanguage,
    }),
  })
  if (!response.ok) {
    throw new Error(`Failed to submit code review (status ${response.status})`)
  }
  return response.json()
}

export async function getCodeReviews() {
  const response = await fetch(`${API_BASE_URL}/code-reviews/`)
  if (!response.ok) {
    throw new Error(`Failed to load code reviews (status ${response.status})`)
  }
  return response.json()
}


// Stage 6: history dashboard endpoints; uses the existing backend.
export async function getReviewHistory({ q = '', language = '', status = '', limit = 8, offset = 0 } = {}) {
  const params = new URLSearchParams({ q, language, status, limit: String(limit), offset: String(offset) })
  const response = await fetch(`${API_BASE_URL}/review-history/?${params}`)
  if (!response.ok) throw new Error(`History request failed (${response.status})`)
  return response.json()
}

// Stats use the same filters as the list, so the totals match what is shown.
export async function getReviewHistoryStats({ q = '', language = '', status = '' } = {}) {
  const params = new URLSearchParams({ q, language, status })
  const response = await fetch(`${API_BASE_URL}/review-history/stats?${params}`)
  if (!response.ok) throw new Error(`History stats failed (${response.status})`)
  return response.json()
}

// Full review (code + issues) for the detail view.
export async function getReviewHistoryDetail(reviewId) {
  const response = await fetch(`${API_BASE_URL}/review-history/${encodeURIComponent(reviewId)}`)
  if (!response.ok) {
    const error = new Error(`Review request failed (${response.status})`)
    error.status = response.status
    throw error
  }
  return response.json()
}
