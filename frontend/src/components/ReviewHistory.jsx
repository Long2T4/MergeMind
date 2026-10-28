import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LANGUAGE_LABELS, LANGUAGES, languageLabel } from '../constants/languages'
import { projectLabel } from '../constants/projects'
import { historySearchString, useHistoryFilters } from '../hooks/useHistoryFilters'
import { useProjects } from '../hooks/useProjects'
import { formatDateTime, formatShortDate, pluralize } from '../lib/format'
import { getReviewHistory, getReviewHistoryStats } from '../services/api'
import Icon from './layout/Icon'
import EmptyState from './ui/EmptyState'
import SeverityBar from './ui/SeverityBar'
import StatusBadge from './ui/StatusBadge'
import './ReviewHistory.css'

const PAGE_SIZE = 8
const SEARCH_DEBOUNCE_MS = 300
const STATUS_OPTIONS = [
  ['', 'All'],
  ['completed', 'Completed'],
  ['pending', 'Pending'],
  ['failed', 'Failed'],
]

function severityCounts(review) {
  const high = review.high_severity_count ?? 0
  // Older API responses only had the high count.
  if (review.medium_severity_count == null || review.low_severity_count == null) {
    return { high, medium: 0, low: 0, split: false }
  }
  return { high, medium: review.medium_severity_count, low: review.low_severity_count, split: true }
}

function IssueTrend({ items, stats, hasFilters }) {
  const bars = items.filter((item) => item.review_status === 'completed').slice().reverse()
  const max = Math.max(1, ...bars.map((item) => item.issue_count))
  const average = stats && stats.completed_reviews > 0
    ? (stats.total_issues / stats.completed_reviews).toFixed(1)
    : null

  return (
    <section className="card trend-card" aria-labelledby="trend-title">
      <div className="trend-summary">
        <h2 id="trend-title" className="trend-label">Issues per review</h2>
        <p className="trend-value">
          <span className="trend-number">{average ?? '—'}</span>
          <span className="muted">
            avg over {pluralize(stats?.completed_reviews ?? 0, 'completed review')}
          </span>
        </p>
        <ul className="legend" aria-label="Severity colours">
          <li><span className="legend-dot is-high" />High</li>
          <li><span className="legend-dot is-medium" />Medium</li>
          <li><span className="legend-dot is-low" />Low</li>
        </ul>
        <p className="trend-scope">
          {hasFilters ? 'Totals for reviews matching the current filters' : 'Totals for all reviews'}
          {stats && (
            <>: {pluralize(stats.total_reviews, 'review')} · {pluralize(stats.total_issues, 'issue')} · {stats.high_severity_issues} high</>
          )}
        </p>
      </div>

      <div className="trend-chart">
        {bars.length === 0 ? (
          <p className="trend-empty">No completed reviews on this page to chart.</p>
        ) : (
          <ol className="trend-bars" aria-label="Issues per completed review on this page, oldest first">
            {bars.map((item) => {
              const { high, medium, low, split } = severityCounts(item)
              const other = split ? 0 : Math.max(0, item.issue_count - high)
              return (
                <li key={item.id} className="trend-bar">
                  <span className="trend-stack-area" aria-hidden="true">
                    <span
                      className={`trend-stack ${item.issue_count === 0 ? 'is-zero' : ''}`}
                      style={{ height: `${(item.issue_count / max) * 100}%` }}
                    >
                      {high > 0 && <span className="is-high" style={{ flexGrow: high }} />}
                      {medium > 0 && <span className="is-medium" style={{ flexGrow: medium }} />}
                      {low > 0 && <span className="is-low" style={{ flexGrow: low }} />}
                      {other > 0 && <span className="is-other" style={{ flexGrow: other }} />}
                    </span>
                  </span>
                  <span className="trend-date" aria-hidden="true">{formatShortDate(item.created_at)}</span>
                  <span className="sr-only">
                    Review #{item.id}, {formatShortDate(item.created_at)}: {pluralize(item.issue_count, 'issue')}
                    {split && ` (${high} high, ${medium} medium, ${low} low)`}
                  </span>
                </li>
              )
            })}
          </ol>
        )}
        <p className="trend-caption">Bars show the completed reviews on this page.</p>
      </div>
    </section>
  )
}

function ReviewHistory() {
  const [filters, setFilters] = useHistoryFilters()
  const { search, language, status, page } = filters
  const navigate = useNavigate()
  const { byId } = useProjects()
  const [searchInput, setSearchInput] = useState(search)
  const [result, setResult] = useState({ items: [], total: 0 })
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  // The last search value this component wrote to the URL.
  const committedSearch = useRef(search)

  // The URL changed from outside (sidebar link, Back/Forward): show its search.
  useEffect(() => {
    if (search !== committedSearch.current) {
      committedSearch.current = search
      setSearchInput(search)
    }
  }, [search])

  // Apply the typed search only after a short pause instead of on every keystroke.
  useEffect(() => {
    if (searchInput === search) return undefined
    const timer = setTimeout(() => {
      committedSearch.current = searchInput
      setFilters((prev) => ({ ...prev, search: searchInput, page: 0 }))
    }, SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [searchInput, search, setFilters])

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
  }, [search, language, status, page, attempt])

  // Totals follow the same filters as the list (but not the page).
  useEffect(() => {
    let active = true
    getReviewHistoryStats({ q: search, language, status })
      .then((data) => { if (active) setStats(data) })
      .catch(() => { if (active) setStats(null) })
    return () => { active = false }
  }, [search, language, status])

  function updateFilter(name, value) {
    setFilters((prev) => ({ ...prev, [name]: value, page: 0 }))
  }

  function goToPage(nextPage) {
    setFilters((prev) => ({ ...prev, page: nextPage }))
  }

  // Commit a search still waiting on the debounce, so it isn't lost when
  // this view unmounts to show the review.
  function openReview(reviewId) {
    const next = searchInput !== search ? { ...filters, search: searchInput, page: 0 } : filters
    if (next !== filters) {
      committedSearch.current = searchInput
      setFilters(next)
    }
    navigate(`/reviews/${reviewId}`, {
      state: { from: `/history${historySearchString(next)}`, fromLabel: 'Back to history' },
    })
  }

  function retryReview(reviewId) {
    navigate('/reviews/new', { state: { retryReviewId: reviewId } })
  }

  const items = result.items || []
  const totalPages = Math.max(1, Math.ceil(result.total / PAGE_SIZE))
  const hasFilters = Boolean(search || language || status)
  const barScale = Math.max(6, ...items.map((item) => item.issue_count))
  const firstShown = page * PAGE_SIZE + 1
  const lastShown = Math.min(result.total, page * PAGE_SIZE + items.length)

  return (
    <div className="history">
      <IssueTrend items={loading || error ? [] : items} stats={stats} hasFilters={hasFilters} />

      <div className="history-toolbar">
        <div className="search-field">
          <Icon name="search" size={16} />
          <label className="sr-only" htmlFor="history-search">Search code or language</label>
          <input
            id="history-search"
            type="search"
            className="input"
            placeholder="Search code or language..."
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
        </div>

        <div className="segmented" role="group" aria-label="Review status">
          {STATUS_OPTIONS.map(([value, label]) => (
            <button
              key={label}
              type="button"
              aria-pressed={status === value}
              onClick={() => updateFilter('status', value)}
            >
              {label}
            </button>
          ))}
        </div>

        <label className="sr-only" htmlFor="history-language">Language</label>
        <select
          id="history-language"
          className="select history-language"
          value={language}
          onChange={(event) => updateFilter('language', event.target.value)}
        >
          <option value="">All languages</option>
          {LANGUAGES.map((lang) => (
            <option key={lang} value={lang}>{LANGUAGE_LABELS[lang]}</option>
          ))}
        </select>
      </div>

      <div className="card table-card history-table-card">
        <div className="history-list-header">
          <h2 className="card-title">Past code reviews</h2>
          <span>{result.total} result{result.total === 1 ? '' : 's'}</span>
        </div>

        {loading && <p className="history-message" role="status">Loading reviews...</p>}
        {error && (
          <div className="notice notice-error history-message" role="alert">
            <span>{error}</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAttempt((n) => n + 1)}>
              Try again
            </button>
          </div>
        )}
        {!loading && !error && items.length === 0 && result.total === 0 && (
          <EmptyState title="No reviews match these filters.">
            Try another search or submit some code.
          </EmptyState>
        )}
        {!loading && !error && items.length === 0 && result.total > 0 && (
          <EmptyState
            title="No reviews on this page."
            action={<button type="button" className="btn btn-secondary btn-sm" onClick={() => goToPage(0)}>Go to first page</button>}
          />
        )}

        {!loading && !error && items.length > 0 && (
          <table className="data-table history-table stack-table">
            <caption className="sr-only">Saved code reviews</caption>
            <thead>
              <tr>
                <th scope="col">Project</th>
                <th scope="col">Language</th>
                <th scope="col">Status</th>
                <th scope="col">Issues</th>
                <th scope="col">Date</th>
                <th scope="col"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {items.map((review) => {
                const counts = severityCounts(review)
                return (
                  <tr key={review.id}>
                    <td data-label="Project">
                      <div className="cell-project">
                        <span className="folder-tile" aria-hidden="true"><Icon name="folder" size={16} /></span>
                        <div className="cell-project-text">
                          <span className="cell-project-name">
                            {projectLabel(byId.get(review.project_id), review.project_id)}
                          </span>
                          <code className="cell-project-sub">
                            Review #{review.id} · {(review.code_preview || '').trim() || '(empty submission)'}
                          </code>
                        </div>
                      </div>
                    </td>
                    <td data-label="Language" className="mono">{languageLabel(review.programming_language)}</td>
                    <td data-label="Status"><StatusBadge status={review.review_status} /></td>
                    <td data-label="Issues">
                      {review.review_status === 'completed' ? (
                        counts.split ? (
                          <SeverityBar high={counts.high} medium={counts.medium} low={counts.low} scale={barScale} />
                        ) : (
                          <SeverityBar high={counts.high} scale={barScale} label={`${review.issue_count} (${counts.high}H)`} />
                        )
                      ) : (
                        <SeverityBar label="n/a" />
                      )}
                    </td>
                    <td data-label="Date" className="cell-date">
                      <time dateTime={review.created_at}>{formatDateTime(review.created_at)}</time>
                    </td>
                    <td className="cell-action">
                      {review.review_status === 'failed' && (
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => retryReview(review.id)}
                          aria-label={`Retry review ${review.id}`}
                        >
                          Retry
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => openReview(review.id)}
                        aria-label={`Open review ${review.id}`}
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}

        {!loading && !error && result.total > PAGE_SIZE && (
          <nav className="history-pagination" aria-label="Review history pages">
            <span className="muted">
              {items.length > 0 ? `Showing ${firstShown}–${lastShown} of ${result.total}` : `${result.total} reviews`}
            </span>
            <div className="history-pagination-controls">
              <button type="button" className="btn btn-secondary btn-sm" disabled={page === 0} onClick={() => goToPage(page - 1)}>
                Previous
              </button>
              <span>Page {page + 1} of {totalPages}</span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={page + 1 >= totalPages}
                onClick={() => goToPage(page + 1)}
              >
                Next
              </button>
            </div>
          </nav>
        )}
      </div>
    </div>
  )
}

export default ReviewHistory
