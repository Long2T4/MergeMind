// Central place for all backend API calls.
// Keeping this separate means components don't need to know the backend URL.
const API_BASE_URL = 'http://localhost:8000'

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
