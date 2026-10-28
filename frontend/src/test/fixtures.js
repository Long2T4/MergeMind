// Synthetic API payloads shaped like the FastAPI responses.
export const PROJECTS = [
  { id: 1, user_id: 1, name: 'Login App', description: 'User authentication', created_at: '2026-10-01T10:00:00' },
]

export const STATS = { total_reviews: 12, completed_reviews: 10, total_issues: 25, high_severity_issues: 4 }

export function historyItem(overrides = {}) {
  return {
    id: 1,
    project_id: 1,
    programming_language: 'python',
    review_status: 'completed',
    created_at: '2026-10-09T14:15:00',
    code_preview: "print('hello')",
    issue_count: 4,
    high_severity_count: 1,
    medium_severity_count: 2,
    low_severity_count: 1,
    ...overrides,
  }
}

export function issue(overrides = {}) {
  return {
    id: 11,
    review_id: 5,
    title: 'SQL injection risk',
    category: 'security',
    severity: 'high',
    file_name: null,
    line_number: 2,
    explanation: 'User input is dropped straight into the SQL string.',
    why_it_matters: 'Someone could read or wipe the users table.',
    suggested_fix: 'Use a parameterised query: `cursor.execute(query, (name,))`',
    confidence_score: 20,
    confidence_level: 'low',
    confidence_evidence: { ai: true },
    status: 'open',
    created_at: '2026-10-09T14:15:00',
    ...overrides,
  }
}

export function review(overrides = {}) {
  return {
    id: 5,
    project_id: 1,
    submitted_code: 'import sqlite3\nquery = f"SELECT * FROM users WHERE name = \'{name}\'"\ncursor.execute(query)',
    programming_language: 'python',
    review_status: 'completed',
    created_at: '2026-10-09T14:15:00',
    risk_score: 72,
    risk_level: 'high',
    risk_breakdown: { security: 60, testing: 0, maintainability: 15, performance: 5 },
    issues: [issue()],
    ...overrides,
  }
}

// Sensible defaults for every function in services/api (auto-mocked).
export function mockApi(api) {
  api.getHealth.mockResolvedValue({ status: 'ok' })
  api.getProjects.mockResolvedValue(PROJECTS)
  api.getReviewHistory.mockResolvedValue({ items: [historyItem()], total: 1, limit: 8, offset: 0 })
  api.getReviewHistoryStats.mockResolvedValue(STATS)
  api.getReviewHistoryDetail.mockResolvedValue(review())
  api.getCodeReviews.mockResolvedValue([review()])
  api.createCodeReview.mockResolvedValue(review({ id: 42 }))
}
