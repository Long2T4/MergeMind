import { countLines } from '../lib/code'
import { pluralize } from '../lib/format'

// Scroll to a finding, open it if it's collapsed, and move focus to it.
// (A plain #hash link would push a history entry and drop the router state
// that powers the "Back to …" link.)
function revealIssue(issueId) {
  const header = document.querySelector(`#issue-${issueId} .issue-card-header`)
  if (!header) return
  if (header.getAttribute('aria-expanded') === 'false') header.click()
  header.scrollIntoView({ block: 'start', behavior: 'smooth' })
  header.focus({ preventScroll: true })
}

// "Where the issues are": each finding's reported line, placed along the
// length of the submitted code.
function IssueLocations({ issues, code }) {
  const totalLines = Math.max(1, countLines(code))
  const located = issues
    .filter((issue) => Number.isInteger(issue.line_number) && issue.line_number >= 1)
    .sort((a, b) => a.line_number - b.line_number)
  const unlocated = issues.length - located.length

  return (
    <section className="card locations-card" aria-labelledby="locations-title">
      <h2 id="locations-title" className="card-title">Where the issues are</h2>

      {located.length === 0 ? (
        <p className="card-meta locations-empty">These findings don't include line numbers.</p>
      ) : (
        <div className="locations">
          <div className="locations-track" aria-hidden="true">
            {located.map((issue) => {
              const line = Math.min(issue.line_number, totalLines)
              const top = totalLines > 1 ? ((line - 1) / (totalLines - 1)) * 100 : 0
              return (
                <span
                  key={issue.id}
                  className={`locations-dot dot-${String(issue.severity).toLowerCase()}`}
                  style={{ top: `${top}%` }}
                />
              )
            })}
          </div>
          <ol className="locations-list">
            {located.map((issue) => (
              <li key={issue.id}>
                <button type="button" className="locations-link" onClick={() => revealIssue(issue.id)}>
                  <span className={`locations-marker dot-${String(issue.severity).toLowerCase()}`} aria-hidden="true" />
                  <span className="mono">line {issue.line_number}</span>
                  <span className="locations-title">{issue.title || 'Code review finding'}</span>
                </button>
              </li>
            ))}
          </ol>
        </div>
      )}

      {unlocated > 0 && located.length > 0 && (
        <p className="card-meta">{pluralize(unlocated, 'finding')} without a line number.</p>
      )}
    </section>
  )
}

export default IssueLocations
