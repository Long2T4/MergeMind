import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { categoryLabel, normalizeCategory } from '../constants/categories'
import { countLines } from '../lib/code'
import { pluralize } from '../lib/format'
import IssueCard from './IssueCard'
import IssueLocations from './IssueLocations'
import Icon from './layout/Icon'
import ReviewSummary from './ReviewSummary'
import RiskScoreCard from './RiskScoreCard'
import CodeBlock from './ui/CodeBlock'
import EmptyState from './ui/EmptyState'

function countCategories(issues) {
  const counts = new Map()
  for (const issue of issues) {
    const key = normalizeCategory(issue.category)
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  return [...counts.entries()]
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count || a.category.localeCompare(b.category))
}

// Full review results: summary header, filterable findings, submitted code,
// and the analysis sidebar (merge risk + issue locations).
function ReviewDetail({ review, projectName }) {
  const [category, setCategory] = useState('all')
  const issues = review.issues || []
  const categories = useMemo(() => countCategories(issues), [issues])
  const visible = category === 'all'
    ? issues
    : issues.filter((issue) => normalizeCategory(issue.category) === category)
  const flaggedLines = issues.map((issue) => issue.line_number).filter(Number.isInteger)

  return (
    <div className="review-results">
      <ReviewSummary review={review} projectName={projectName} />

      {review.review_status === 'failed' && (
        <div className="notice notice-error results-failed">
          <span>
            The AI review didn't complete, so there are no findings or risk score for this
            submission. Your code was saved.
          </span>
          <Link to="/reviews/new" state={{ retryReviewId: review.id }} className="btn btn-secondary btn-sm">
            <Icon name="refresh" size={16} />
            Retry review
          </Link>
        </div>
      )}

      <div className="results-grid">
        <div className="results-main">
          <h2 className="sr-only">Findings</h2>
          {issues.length > 0 && (
            <div className="chip-row" role="group" aria-label="Filter findings by category">
              <button
                type="button"
                className="chip"
                aria-pressed={category === 'all'}
                onClick={() => setCategory('all')}
              >
                All · {issues.length}
              </button>
              {categories.map((entry) => (
                <button
                  key={entry.category}
                  type="button"
                  className="chip"
                  aria-pressed={category === entry.category}
                  onClick={() => setCategory(entry.category)}
                >
                  {categoryLabel(entry.category)} · {entry.count}
                </button>
              ))}
            </div>
          )}

          {issues.length === 0 ? (
            <div className="card">
              <EmptyState
                title={review.review_status === 'completed'
                  ? 'No issues found — nice work!'
                  : 'No issues to show for this review.'}
              />
            </div>
          ) : (
            <ul className="issue-list">
              {visible.map((issue, index) => (
                <IssueCard
                  key={issue.id}
                  issue={issue}
                  code={review.submitted_code}
                  language={review.programming_language}
                  defaultExpanded={index === 0}
                />
              ))}
            </ul>
          )}

          {issues.length > 0 && (
            <p className="results-footnote">
              Marking findings as fixed or as false positives is planned for Stage 9 and isn't available yet.
            </p>
          )}

          <details className="card submitted-code" open>
            <summary>
              <span className="card-title">Submitted code</span>
              <span className="card-meta">{pluralize(countLines(review.submitted_code), 'line')}</span>
            </summary>
            <CodeBlock
              code={review.submitted_code}
              language={review.programming_language}
              flaggedLines={flaggedLines}
              label="Submitted code"
            />
          </details>
        </div>

        <aside className="results-aside" aria-label="Review analysis">
          <RiskScoreCard review={review} />
          {issues.length > 0 && <IssueLocations issues={issues} code={review.submitted_code} />}
          <section className="card learning-link-card">
            <p className="eyebrow">Learning</p>
            <p className="learning-link-title">See which categories come up across all your reviews.</p>
            <Link to="/learning" className="text-link">Open Learning →</Link>
          </section>
        </aside>
      </div>
    </div>
  )
}

export default ReviewDetail
