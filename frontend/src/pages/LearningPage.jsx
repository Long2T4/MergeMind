import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import FormattedText from '../components/FormattedText'
import ComingSoon from '../components/ui/ComingSoon'
import EmptyState from '../components/ui/EmptyState'
import { CATEGORY_GUIDANCE, categoryLabel } from '../constants/categories'
import { formatShortDate, pluralize } from '../lib/format'
import {
  activityGrid, categoryTrend, filterByRange, repeatedCategories, summarizeFindings,
} from '../lib/learning'
import { getCodeReviews, getReviewHistoryStats } from '../services/api'
import './pages.css'

const RANGES = [
  ['all', 'All time'],
  ['30d', 'Last 30 days'],
]
const TABS = [
  ['overview', 'Overview'],
  ['repeated', 'Repeated categories'],
  ['guidance', 'Guidance'],
]
const BAR_COLORS = ['var(--high)', 'var(--medium)', 'var(--low)', 'var(--violet)', 'var(--success)', '#8e97a5', '#f472b6', '#2dd4bf']
const FROM_LEARNING = { from: '/learning', fromLabel: 'Back to learning' }
const SHARED_CATEGORY_NOTE =
  "Findings that share a category aren't necessarily the same mistake, so open the reviews to compare them."

function heatLevel(count, max) {
  if (count === 0 || max === 0) return 0
  return Math.max(1, Math.ceil((count / max) * 4))
}

function coverageText(loadedCount, stats) {
  if (stats && stats.total_reviews > loadedCount) {
    return `Based on ${loadedCount} of ${stats.total_reviews} saved reviews. The rest weren't loaded, so these numbers are incomplete.`
  }
  if (!stats) return `Based on the ${pluralize(loadedCount, 'review')} loaded from the server.`
  return `Based on all ${pluralize(loadedCount, 'saved review')}.`
}

function CategoryBars({ categories, rangeLabel }) {
  const max = Math.max(1, ...categories.map((entry) => entry.count))
  return (
    <section className="card" aria-labelledby="categories-title">
      <div className="card-header">
        <h2 id="categories-title" className="card-title">Where your issues come from</h2>
        <span className="card-meta">{rangeLabel}</span>
      </div>
      {categories.length === 0 ? (
        <p className="muted">No findings in this period.</p>
      ) : (
        <ul className="category-bars">
          {categories.map((entry, index) => (
            <li key={entry.category}>
              <div className="category-bar-label">
                <span>{categoryLabel(entry.category)}</span>
                <span className="mono" aria-hidden="true">{entry.count}</span>
                <span className="sr-only">
                  {pluralize(entry.count, 'finding')} in {pluralize(entry.reviewCount, 'review')}
                </span>
              </div>
              <div className="category-bar-track" aria-hidden="true">
                <div
                  className="category-bar-fill"
                  style={{ width: `${(entry.count / max) * 100}%`, background: BAR_COLORS[index % BAR_COLORS.length] }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="card-meta card-footnote">Each finding is counted once, under the category the AI assigned.</p>
    </section>
  )
}

function ActivityCard({ activity }) {
  return (
    <section className="card activity-card" aria-labelledby="activity-title">
      <div className="card-header">
        <h2 id="activity-title" className="card-title">Activity</h2>
        <span className="card-meta">12 weeks</span>
      </div>
      <div
        className="heatmap"
        role="img"
        aria-label={`${pluralize(activity.total, 'review')} submitted in the last 12 weeks`}
      >
        {activity.columns.map((column) => (
          <div className="heatmap-col" key={column[0].key}>
            {column.map((cell) => (
              <span
                key={cell.key}
                className={`heatmap-cell ${cell.future ? 'is-future' : `level-${heatLevel(cell.count, activity.max)}`}`}
                title={cell.future ? undefined : `${formatShortDate(cell.date)}: ${pluralize(cell.count, 'review')}`}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="heatmap-legend">
        <span className="card-meta">Reviews submitted per day</span>
        <span className="heatmap-scale" aria-hidden="true">
          Less
          {[0, 1, 2, 3, 4].map((level) => <span key={level} className={`heatmap-cell level-${level}`} />)}
          More
        </span>
      </div>
    </section>
  )
}

function RepeatedHighlight({ entry, reviewsById, onShowAll }) {
  const { issue, reviewId } = entry.example
  const language = reviewsById.get(reviewId)?.programming_language
  return (
    <section className="card repeated-highlight" aria-labelledby="repeated-highlight-title">
      <div className="repeated-highlight-text">
        <span className="repeated-badge">Flagged in {entry.reviews.length} reviews</span>
        <h2 id="repeated-highlight-title" className="repeated-title">{categoryLabel(entry.category)}</h2>
        <p className="muted">
          {pluralize(entry.findingCount, 'finding')} in this category across{' '}
          {pluralize(entry.reviews.length, 'review')}. {SHARED_CATEGORY_NOTE}
        </p>
        {CATEGORY_GUIDANCE[entry.category] && (
          <p className="repeated-guidance">
            <span className="eyebrow">General guidance</span>
            {CATEGORY_GUIDANCE[entry.category]}
          </p>
        )}
        <div className="repeated-actions">
          <Link to={`/reviews/${reviewId}`} state={FROM_LEARNING} className="btn btn-primary">
            Open latest review
          </Link>
          <button type="button" className="btn btn-secondary" onClick={onShowAll}>
            See all repeated categories
          </button>
        </div>
      </div>
      <div className="repeated-highlight-code">
        <p className="eyebrow">Latest finding · Review #{reviewId}</p>
        <p className="repeated-issue-title">{issue.title || 'Code review finding'}</p>
        {issue.suggested_fix ? (
          <>
            <p className="eyebrow repeated-fix-label">Suggested fix</p>
            <FormattedText text={issue.suggested_fix} language={language} />
          </>
        ) : (
          <FormattedText text={issue.explanation} language={language} />
        )}
      </div>
    </section>
  )
}

function CategoryTrend({ trend }) {
  return (
    <section className="card" aria-labelledby="trend-categories-title">
      <div className="card-header">
        <h2 id="trend-categories-title" className="card-title">Findings per review, by category</h2>
        <span className="card-meta">Last {pluralize(trend.reviews.length, 'completed review')}</span>
      </div>
      {trend.reviews.length < 2 || trend.series.length === 0 ? (
        <p className="muted">Run at least two completed reviews with findings to compare categories over time.</p>
      ) : (
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Findings per review, by category">
          <table className="data-table trend-table">
            <thead>
              <tr>
                <th scope="col">Category</th>
                {trend.reviews.map((review) => (
                  <th scope="col" key={review.id}>
                    <Link to={`/reviews/${review.id}`} state={FROM_LEARNING}>#{review.id}</Link>
                    <span className="trend-table-date">{formatShortDate(review.created_at)}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {trend.series.map((row) => (
                <tr key={row.category}>
                  <th scope="row">{categoryLabel(row.category)}</th>
                  {row.counts.map((count, index) => (
                    <td key={trend.reviews[index].id} className="mono">{count}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="card-meta card-footnote">
        Counts depend on the code you submitted each time, so a lower number isn&apos;t proof of improvement.
      </p>
    </section>
  )
}

function RepeatedList({ repeated }) {
  return (
    <>
      <p className="notice notice-info">
        These categories were flagged in more than one review. {SHARED_CATEGORY_NOTE}
      </p>
      {repeated.length === 0 ? (
        <div className="card">
          <EmptyState title="No repeated categories yet">
            A category appears here once it has been flagged in at least two different reviews.
          </EmptyState>
        </div>
      ) : (
        <ul className="repeated-list">
          {repeated.map((entry) => (
            <li key={entry.category} className="card repeated-item">
              <div>
                <h3 className="card-title">{categoryLabel(entry.category)}</h3>
                <p className="card-meta">
                  Flagged in {pluralize(entry.reviews.length, 'review')} · {pluralize(entry.findingCount, 'finding')} ·
                  last seen {formatShortDate(entry.reviews[0].created_at)}
                </p>
              </div>
              <div className="review-links" aria-label={`Reviews with ${categoryLabel(entry.category)} findings`}>
                {entry.reviews.map((review) => (
                  <Link key={review.id} to={`/reviews/${review.id}`} state={FROM_LEARNING} className="tag">
                    #{review.id}
                  </Link>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function GuidanceList({ categories }) {
  return (
    <>
      <div className="notice notice-info guidance-intro">
        <span>General guidance for the categories found in your reviews. Personalised lessons aren&apos;t available yet.</span>
        <ComingSoon label="Lessons coming soon" />
      </div>
      {categories.length === 0 ? (
        <div className="card"><EmptyState title="No findings yet">Guidance appears once your reviews have findings.</EmptyState></div>
      ) : (
        <ul className="guidance-list">
          {categories.map((entry) => (
            <li key={entry.category} className="card guidance-item">
              <div className="guidance-head">
                <h3 className="card-title">{categoryLabel(entry.category)}</h3>
                <span className="card-meta">{pluralize(entry.count, 'finding')}</span>
              </div>
              <p className="muted">
                {CATEGORY_GUIDANCE[entry.category] ||
                  'Compare the findings in this category with their suggested fixes to spot what they have in common.'}
              </p>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function LearningPage() {
  const [reviews, setReviews] = useState(null)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [range, setRange] = useState('all')
  const [tab, setTab] = useState('overview')

  useEffect(() => {
    let active = true
    setError(false)
    setReviews(null)
    // GET /code-reviews/ returns every saved review (it isn't paginated);
    // the stats total is used to check that nothing is missing.
    Promise.all([getCodeReviews(), getReviewHistoryStats().catch(() => null)])
      .then(([allReviews, totals]) => {
        if (!active) return
        setReviews(allReviews || [])
        setStats(totals)
      })
      .catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [attempt])

  const derived = useMemo(() => {
    if (!reviews) return null
    const inRange = filterByRange(reviews, range)
    const summary = summarizeFindings(inRange)
    return {
      inRange,
      summary,
      repeated: repeatedCategories(inRange),
      trend: categoryTrend(inRange, summary.categories.slice(0, 4).map((entry) => entry.category)),
      activity: activityGrid(reviews),
      reviewsById: new Map(reviews.map((review) => [review.id, review])),
    }
  }, [reviews, range])

  function handleTabKey(event) {
    const index = TABS.findIndex(([id]) => id === tab)
    let next = null
    if (event.key === 'ArrowRight') next = TABS[(index + 1) % TABS.length][0]
    if (event.key === 'ArrowLeft') next = TABS[(index - 1 + TABS.length) % TABS.length][0]
    if (event.key === 'Home') next = TABS[0][0]
    if (event.key === 'End') next = TABS[TABS.length - 1][0]
    if (next) {
      event.preventDefault()
      setTab(next)
      document.getElementById(`learning-tab-${next}`)?.focus()
    }
  }

  if (error) {
    return (
      <div className="learning">
        <h1 className="page-title learning-error-title">Your learning profile</h1>
        <div className="notice notice-error" role="alert">
          <span>Could not load your reviews. Check the backend connection.</span>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAttempt((n) => n + 1)}>
            Try again
          </button>
        </div>
      </div>
    )
  }

  if (!derived) {
    return (
      <div className="learning" role="status" aria-label="Loading learning profile">
        <div className="skeleton" style={{ height: 200, marginBottom: 20 }} />
        <div className="skeleton" style={{ height: 280 }} />
      </div>
    )
  }

  const { inRange, summary, repeated, trend, activity, reviewsById } = derived
  const rangeLabel = range === '30d' ? 'last 30 days' : 'all time'

  return (
    <div className="learning">
      <section className="card learning-hero">
        <div className="learning-hero-text">
          <p className="learning-eyebrow">Learning profile · {rangeLabel}</p>
          <h1 className="learning-title">Your learning profile</h1>
          <p className="learning-sub">
            MergeMind groups the findings from your reviews by category, so you can see which kinds of
            issues come up most often.
          </p>
          <p className="learning-coverage">
            {coverageText(reviews.length, stats)}
            {range === '30d' && ` ${pluralize(inRange.length, 'review')} in the last 30 days.`}
          </p>
          <div className="segmented" role="group" aria-label="Time range">
            {RANGES.map(([value, label]) => (
              <button key={value} type="button" aria-pressed={range === value} onClick={() => setRange(value)}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <dl className="learning-stats">
          <div className="learning-stat"><dt>Reviews</dt><dd>{summary.reviewCount}</dd></div>
          <div className="learning-stat"><dt>Issues found</dt><dd className="tone-success">{summary.issueCount}</dd></div>
          <div className="learning-stat"><dt>Categories flagged</dt><dd>{summary.categories.length}</dd></div>
          <div className="learning-stat"><dt>High severity</dt><dd className="tone-high">{summary.highCount}</dd></div>
        </dl>
      </section>

      {reviews.length === 0 ? (
        <div className="card">
          <EmptyState
            title="No reviews yet"
            action={<Link to="/reviews/new" className="btn btn-primary btn-sm">Start a review</Link>}
          >
            Your learning profile fills in as you run reviews.
          </EmptyState>
        </div>
      ) : (
        <>
          <div className="tabs" role="tablist" aria-label="Learning sections" onKeyDown={handleTabKey}>
            {TABS.map(([id, label]) => (
              <button
                key={id}
                id={`learning-tab-${id}`}
                type="button"
                role="tab"
                className="tab"
                aria-selected={tab === id}
                aria-controls={`learning-panel-${id}`}
                tabIndex={tab === id ? 0 : -1}
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Every panel stays in the DOM (hidden when inactive) so each tab's aria-controls resolves. */}
          <div className="tab-panel" role="tabpanel" id="learning-panel-overview" aria-labelledby="learning-tab-overview" tabIndex={0} hidden={tab !== 'overview'}>
            <div className="learning-grid">
              <CategoryBars categories={summary.categories} rangeLabel={rangeLabel} />
              <ActivityCard activity={activity} />
            </div>
            {repeated[0] && (
              <RepeatedHighlight
                entry={repeated[0]}
                reviewsById={reviewsById}
                onShowAll={() => setTab('repeated')}
              />
            )}
            <CategoryTrend trend={trend} />
          </div>
          <div className="tab-panel" role="tabpanel" id="learning-panel-repeated" aria-labelledby="learning-tab-repeated" tabIndex={0} hidden={tab !== 'repeated'}>
            <RepeatedList repeated={repeated} />
          </div>
          <div className="tab-panel" role="tabpanel" id="learning-panel-guidance" aria-labelledby="learning-tab-guidance" tabIndex={0} hidden={tab !== 'guidance'}>
            <GuidanceList categories={summary.categories} />
          </div>
        </>
      )}

      <p className="page-footnote">
        Fix rates, streaks and lessons need finding feedback (planned for Stage 9), so they aren&apos;t shown yet.
      </p>
    </div>
  )
}

export default LearningPage
