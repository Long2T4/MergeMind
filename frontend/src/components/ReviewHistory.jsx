import { useEffect, useState } from 'react'
import { getReviewHistory, getReviewHistoryStats } from '../services/api'
import { LANGUAGES, LANGUAGE_LABELS } from '../constants/languages'
import './ReviewHistory.css'

const PAGE_SIZE = 8
const SEARCH_DEBOUNCE_MS = 300

// Filters and page live in the parent (HomePage) so they survive opening a
// review and coming back.
function ReviewHistory({ filters, onFiltersChange, onSelectReview, onBack }) {
  const { search, language, status, page } = filters
  const [searchInput, setSearchInput] = useState(search)
  const [result, setResult] = useState({ items: [], total: 0 })
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Apply the typed search only after a short pause instead of on every keystroke.
  useEffect(() => {
    if (searchInput === search) return undefined
    const timer = setTimeout(() => {
      onFiltersChange((prev) => ({ ...prev, search: searchInput, page: 0 }))
    }, SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [searchInput, search, onFiltersChange])

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

  // Totals follow the same filters as the list (but not the page).
  useEffect(() => {
    let active = true
    getReviewHistoryStats({ q: search, language, status })
      .then((data) => { if (active) setStats(data) })
      .catch(() => { if (active) setStats(null) })
    return () => { active = false }
  }, [search, language, status])

  function updateFilter(name, value) {
    onFiltersChange((prev) => ({ ...prev, [name]: value, page: 0 }))
  }

  function goToPage(nextPage) {
    onFiltersChange((prev) => ({ ...prev, page: nextPage }))
  }

  // Commit a search still waiting on the debounce, so it isn't lost when
  // this view unmounts to show the review.
  function openReview(reviewId) {
    if (searchInput !== search) {
      onFiltersChange((prev) => ({ ...prev, search: searchInput, page: 0 }))
    }
    onSelectReview(reviewId)
  }

  const totalPages = Math.max(1, Math.ceil(result.total / PAGE_SIZE))
  const items = result.items || []
  const hasFilters = Boolean(search || language || status)

  return (
    <section className="history-dashboard" aria-label="Review history dashboard">
      <div className="history-top">
        <div>
          <button type="button" className="history-back" onClick={onBack}>← Back to submissions</button>
          <h2>Review History</h2>
          <p>Browse completed and previous code reviews in your project.</p>
        </div>
      </div>

      <p className="history-stats-scope">
        {hasFilters ? 'Totals for reviews matching the current filters' : 'Totals for all reviews'}
      </p>
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
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
        </label>
        <label>
          Language
          <select value={language} onChange={(event) => updateFilter('language', event.target.value)}>
            <option value="">All languages</option>
            {LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>{LANGUAGE_LABELS[lang]}</option>
            ))}
          </select>
        </label>
        <label>
          Review status
          <select value={status} onChange={(event) => updateFilter('status', event.target.value)}>
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
          {items.map((review) => (
            <button
              type="button"
              className="history-review"
              key={review.id}
              onClick={() => openReview(review.id)}
              aria-label={`Open review ${review.id}`}
            >
              <div className="history-review-main">
                <div className="history-review-labels">
                  <span className="history-id">Review #{review.id}</span>
                  <span className="history-language">
                    {LANGUAGE_LABELS[review.programming_language] ?? review.programming_language}
                  </span>
                  <span className={`history-status history-status-${review.review_status}`}>{review.review_status}</span>
                </div>
                <code className="history-code-snippet">
                  {(review.code_preview || '').trim() || '(empty submission)'}
                </code>
                <time dateTime={review.created_at}>
                  {new Date(review.created_at).toLocaleString()}
                </time>
              </div>
              <div className="history-review-right">
                <strong>{review.issue_count}</strong>
                <span>issue{review.issue_count === 1 ? '' : 's'}</span>
                {review.high_severity_count > 0 && <small>{review.high_severity_count} high</small>}
                <span className="history-arrow" aria-hidden="true">→</span>
              </div>
            </button>
          ))}
        </div>
      )}

      {!loading && !error && result.total > PAGE_SIZE && (
        <nav className="history-pagination" aria-label="Review history pages">
          <button type="button" disabled={page === 0} onClick={() => goToPage(page - 1)}>Previous</button>
          <span>Page {page + 1} of {totalPages}</span>
          <button type="button" disabled={page + 1 >= totalPages} onClick={() => goToPage(page + 1)}>Next</button>
        </nav>
      )}
    </section>
  )
}

export default ReviewHistory
