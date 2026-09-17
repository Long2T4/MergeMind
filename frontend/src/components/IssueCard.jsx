import { useState } from 'react'
import SeverityBadge from './SeverityBadge'
import CategoryBadge from './CategoryBadge'
import FormattedText from './FormattedText'

function IssueCard({ issue }) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Older issues saved before the title/why_it_matters fields existed may
  // have title: null — fall back to a generic label rather than showing blank.
  const displayTitle = issue.title || 'Code review finding'

  return (
    <li className={`issue-card severity-border-${issue.severity}`}>
      <button
        type="button"
        className="issue-card-header"
        onClick={() => setIsExpanded((prev) => !prev)}
        aria-expanded={isExpanded}
      >
        <div className="issue-card-badges">
          <SeverityBadge severity={issue.severity} />
          <CategoryBadge category={issue.category} />
        </div>
        <span className="issue-card-title">{displayTitle}</span>
        <span className={`issue-card-chevron ${isExpanded ? 'is-open' : ''}`} aria-hidden="true">
          ▾
        </span>
      </button>

      <div className={`issue-card-body ${isExpanded ? 'is-open' : ''}`}>
        <div className="issue-card-body-inner">
          <section className="issue-section">
            <h4>What's wrong?</h4>
            <FormattedText text={issue.explanation} />
          </section>

          {issue.why_it_matters && (
            <section className="issue-section">
              <h4>Why does it matter?</h4>
              <FormattedText text={issue.why_it_matters} />
            </section>
          )}

          {issue.suggested_fix && (
            <section className="issue-section issue-section-fix">
              <h4>How do I fix it?</h4>
              <FormattedText text={issue.suggested_fix} />
            </section>
          )}

          {issue.line_number != null && (
            <span className="issue-line-reference">Line {issue.line_number}</span>
          )}
        </div>
      </div>
    </li>
  )
}

export default IssueCard
