import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { categoryLabel, normalizeCategory } from '../constants/categories'
import { countLines } from '../lib/code'
import { pluralize } from '../lib/format'
import { diffContext } from '../lib/pullRequest'
import IssueCard from './IssueCard'
import IssueLocations from './IssueLocations'
import Icon from './layout/Icon'
import { ChangedFiles, PullRequestHeader } from './PullRequestDetails'
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
function countFiles(issues) {
  const counts = new Map()
  for (const issue of issues) {
    if (issue.file_name) counts.set(issue.file_name, (counts.get(issue.file_name) || 0) + 1)
  }
  return counts
}

function ReviewDetail({ review, projectName }) {
  const [category, setCategory] = useState('all')
  const [file, setFile] = useState('all')
  const issues = review.issues || []
  // Stage 11: set only for pull request reviews.
  const pr = review.pull_request
  const prFiles = useMemo(() => new Map((pr?.files || []).map((item) => [item.path, item])), [pr])
  const categories = useMemo(() => countCategories(issues), [issues])
  const fileCounts = useMemo(() => countFiles(issues), [issues])
  const visible = issues.filter((issue) => (
    (category === 'all' || normalizeCategory(issue.category) === category)
    && (file === 'all' || issue.file_name === file)
  ))
  const flaggedLines = issues.map((issue) => issue.line_number).filter(Number.isInteger)
  const failedFiles = (pr?.files || []).filter((item) => item.review_state === 'failed').length
  const retryState = pr
    ? { retryPullRequest: { prUrl: pr.html_url, projectId: review.project_id, sourceRoot: pr.source_root || '' } }
    : { retryReviewId: review.id }

  return (
    <div className="review-results">
      <ReviewSummary review={review} projectName={projectName} />
      {pr && <PullRequestHeader review={review} />}

      {review.review_status === 'failed' && (
        <div className="notice notice-error results-failed">
          <span>
            {pr
              ? "The pull request review didn't complete, so there are no findings or risk score. Retrying reviews the pull request again."
              : "The AI review didn't complete, so there are no findings or risk score for this submission. Your code was saved."}
          </span>
          <Link to="/reviews/new" state={retryState} className="btn btn-secondary btn-sm">
            <Icon name="refresh" size={16} />
            Retry review
          </Link>
        </div>
      )}
      {review.review_status === 'completed' && failedFiles > 0 && (
        <p className="notice notice-info" role="status">
          {pluralize(failedFiles, 'file')} couldn't be reviewed, so {failedFiles === 1 ? 'it has' : 'they have'} no findings.
          See Changed files below.
        </p>
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
          {fileCounts.size > 1 && (
            <div className="chip-row" role="group" aria-label="Filter findings by file">
              <button type="button" className="chip" aria-pressed={file === 'all'} onClick={() => setFile('all')}>
                All files
              </button>
              {[...fileCounts.entries()].map(([path, count]) => (
                <button
                  key={path}
                  type="button"
                  className="chip mono"
                  aria-pressed={file === path}
                  onClick={() => setFile(path)}
                >
                  {path} · {count}
                </button>
              ))}
            </div>
          )}

          {issues.length === 0 ? (
            <div className="card">
              <EmptyState
                title={review.review_status === 'completed'
                  ? 'No issues found — nice work!'
                  : pr && review.review_status === 'pending'
                    ? 'Findings appear here as each file is reviewed.'
                    : 'No issues to show for this review.'}
              />
            </div>
          ) : (
            <ul className="issue-list">
              {visible.map((issue, index) => {
                const changedFile = pr ? prFiles.get(issue.file_name) : null
                return (
                  <IssueCard
                    key={issue.id}
                    issue={issue}
                    code={review.submitted_code}
                    language={changedFile?.language || review.programming_language}
                    // Pull request findings point into the changed file, not the stored diff.
                    snippet={pr ? diffContext(changedFile?.patch, issue.line_number) : undefined}
                    defaultExpanded={index === 0}
                  />
                )
              })}
            </ul>
          )}

          {issues.length > 0 && (
            <p className="results-footnote">
              Marking findings as fixed or as false positives isn't available yet.
            </p>
          )}

          {pr ? (
            <ChangedFiles pullRequest={pr} issueCounts={fileCounts} />
          ) : (
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
          )}
        </div>

        <aside className="results-aside" aria-label="Review analysis">
          <RiskScoreCard review={review} />
          {/* Line positions only make sense within a single submitted file. */}
          {issues.length > 0 && !pr && <IssueLocations issues={issues} code={review.submitted_code} />}
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
