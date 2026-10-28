import { languageLabel } from '../constants/languages'
import { countLines } from '../lib/code'
import { countBySeverity, formatLongDate, pluralize } from '../lib/format'
import { getRiskSummary } from './RiskScoreCard'
import ScoreRing from './ui/ScoreRing'
import StatusBadge from './ui/StatusBadge'

const SEVERITIES = [
  ['high', 'High'],
  ['medium', 'Medium'],
  ['low', 'Low'],
]

function summarySentence(review, counts) {
  if (review.review_status === 'failed') return "The AI review didn't complete for this submission."
  if (review.review_status === 'pending') return 'This review is still in progress.'
  const total = (review.issues || []).length
  if (total === 0) return 'No issues found — nice work!'
  const parts = `${pluralize(total, 'issue')} found: ${counts.high} high, ${counts.medium} medium, ${counts.low} low.`
  return counts.high > 0
    ? `${parts} Start with the high-severity ${counts.high === 1 ? 'finding' : 'findings'}.`
    : parts
}

// Results header: Stage 8 merge risk ring, review meta and severity counts.
function ReviewSummary({ review, projectName }) {
  const counts = countBySeverity(review.issues)
  const risk = getRiskSummary(review)
  const lines = countLines(review.submitted_code)

  return (
    <section className="card results-header" aria-labelledby="review-title">
      <ScoreRing
        value={risk?.score}
        tone={risk?.level}
        caption="merge risk"
        size={124}
        stroke={11}
        label={risk ? `Merge risk ${risk.score} out of 100, ${risk.level}` : 'Merge risk not available'}
      />

      <div className="results-header-main">
        <div className="results-title-row">
          <h1 id="review-title" className="results-title">{projectName}</h1>
          <StatusBadge status={review.review_status} />
        </div>
        <p className="results-meta">
          Review #{review.id} · {languageLabel(review.programming_language)} · {pluralize(lines, 'line')} ·{' '}
          {formatLongDate(review.created_at)}
        </p>
        <p className="results-summary">{summarySentence(review, counts)}</p>
      </div>

      <div className="severity-tiles" role="list" aria-label="Findings by severity">
        {SEVERITIES.map(([level, label]) => (
          <div key={level} role="listitem" className={`severity-tile tile-${level}`}>
            <span className="severity-tile-count">{counts[level]}</span>
            <span className="severity-tile-label">{label}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export default ReviewSummary
