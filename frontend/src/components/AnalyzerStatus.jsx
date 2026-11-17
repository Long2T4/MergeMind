import { pluralize } from '../lib/format'

// Stage 13: whether Semgrep and Bandit ran for this review, so "no findings"
// can't be mistaken for "the scanner never ran".
const SCANNERS = [
  ['semgrep', 'Semgrep'],
  ['bandit', 'Bandit'],
]

function statusText(status, count) {
  switch (status) {
    case 'completed':
      return count > 0 ? `Checked · supports ${pluralize(count, 'finding')}` : 'Checked · no issues found'
    case 'failed':
      return "Couldn't finish (for example, a syntax error)"
    case 'unavailable':
      return 'Not installed on this server'
    case 'not_run':
      return 'Not run · only Python is scanned'
    default:
      return 'Not recorded'
  }
}

function AnalyzerStatus({ review }) {
  if (review.review_status !== 'completed') return null
  const status = review.analysis_status

  return (
    <section className="card" aria-labelledby="analyzer-status-title">
      <div className="card-header">
        <h2 id="analyzer-status-title" className="card-title">Static analysis</h2>
      </div>
      {status ? (
        <ul className="analyzer-list">
          {SCANNERS.map(([key, name]) => {
            const count = (review.issues || []).filter((issue) => issue.confidence_evidence?.[key] === true).length
            return (
              <li key={key}>
                <span className="mono">{name}</span>
                <span className={status[key] === 'completed' ? 'analyzer-on' : 'analyzer-off'}>
                  {statusText(status[key], count)}
                </span>
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="muted">Not recorded: this review was saved before static analysis was added.</p>
      )}
    </section>
  )
}

export default AnalyzerStatus
