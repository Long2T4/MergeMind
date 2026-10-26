import { useEffect, useState } from 'react'
import { getReviewHistory, getReviewHistoryStats } from '../services/api'
import './ReviewHistory.css'

const PAGE_SIZE = 8

function ReviewHistory({ onSelectReview, onBack }) {
  const [search, setSearch] = useState('')
  const [language, setLanguage] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(0)
  const [result, setResult] = useState({ items: [], total: 0 })
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Refresh automatically when the selected filters change.
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    getReviewHistory({ q: search, language, status, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
      .then((data) => { if (active) setResult(data) })
      .catch(() => { if (active) setError('Could not load review history. Check the backend connection.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [search, language, status, page])

  useEffect(() => {
    getReviewHistoryStats().then(setStats).catch(() => setStats(null))
  }, [])

  const totalPages = Math.max(1, Math.ceil(result.total / PAGE_SIZE))
  const items = result.items || []

  return (
    <section className="history-dashboard" aria-label="Review history dashboard">
      <div className="history-top">
        <div>
          <button type="button" className="history-back" onClick={onBack}>← Back to submissions</button>
          <h2>Review History</h2>
          <p>Browse completed and previous code reviews in your project.</p>
        </div>
      </div>

      <div className="history-stats" aria-label="Review totals">
        <div className="history-stat"><span>Total reviews</span><strong>{stats?.total_reviews ?? '—'}</strong></div>
        <div className="history-stat"><span>Completed</span><strong>{stats?.completed_reviews ?? '—'}</strong></div>
        <div className="history-stat"><span>Issues found</span><strong>{stats?.total_issues ?? '—'}</strong></div>
        <div className="history-stat"><span>High severity</span><strong>{stats?.high_severity_issues ?? '—'}</strong></div>
      </div>

      <div className="history-filters">
        <label>
          Search code or language
          <input
            type="search"
            placeholder="Search previous reviews..."
            value={search}
            onChange={(event) => { setSearch(event.target.value); setPage(0) }}
          />
        </label>
        <label>
          Language
          <select value={language} onChange={(event) => { setLanguage(event.target.value); setPage(0) }}>
            <option value="">All languages</option>
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="java">Java</option>
            <option value="c++">C++</option>
          </select>
        </label>
        <label>
          Review status
          <select value={status} onChange={(event) => { setStatus(event.target.value); setPage(0) }}>
            <option value="">All statuses</option>
            <option value="completed">Completed</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
        </label>
      </div>

      <div className="history-list-header">
        <h3>Past code reviews</h3>
        <span>{result.total} result{result.total === 1 ? '' : 's'}</span>
      </div>

      {loading && <p className="history-message" role="status">Loading reviews...</p>}
      {error && <p className="history-message history-error" role="alert">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="history-message">No reviews match these filters. Try another search or submit some code.</p>
      )}
      {!loading && !error && items.length > 0 && (
        <div className="history-list">
          {items.map((review) => {
            const issueCount = review.issues?.length ?? 0
            const highCount = (review.issues || []).filter((issue) => issue.severity?.toLowerCase() === 'high').length
            return (
              <button
                type="button"
                className="history-review"
                key={review.id}
                onClick={() => onSelectReview(review.id)}
                aria-label={`Open review ${review.id}`}
              >
                <div className="history-review-main">
                  <div className="history-review-labels">
                    <span className="history-id">Review #{review.id}</span>
                    <span className="history-language">{review.programming_language}</span>
                    <span className={`history-status history-status-${review.review_status}`}>{review.review_status}</span>
                  </div>
                  <code className="history-code-snippet">
                    {(review.submitted_code || '').trim().slice(0, 160) || '(empty submission)'}
                  </code>
                  <time dateTime={review.created_at}>
                    {new Date(review.created_at).toLocaleString()}
                  </time>
                </div>
                <div className="history-review-right">
                  <strong>{issueCount}</strong>
                  <span>issue{issueCount === 1 ? '' : 's'}</span>
                  {highCount > 0 && <small>{highCount} high</small>}
                  <span className="history-arrow" aria-hidden="true">→</span>
                </div>
              </button>
            )
          })}
        </div>
      )}

      {!loading && !error && result.total > PAGE_SIZE && (
        <nav className="history-pagination" aria-label="Review history pages">
          <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <span>Page {page + 1} of {totalPages}</span>
          <button type="button" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
        </nav>
      )}
    </section>
  )
}

export default ReviewHistory
