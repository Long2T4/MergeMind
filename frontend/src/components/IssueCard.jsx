
import { useState } from 'react'
import SeverityBadge from './SeverityBadge'
import CategoryBadge from './CategoryBadge'
import FormattedText from './FormattedText'

function IssueCard({ issue }) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Older issues saved before the title/why_it_matters fields existed may
  // have title: null — fall back to a generic label rather than showing blank.
  const displayTitle = issue.title || 'Code review finding'

  const confidenceScore = issue.confidence_score
  const confidenceLevel = issue.confidence_level
  const confidenceEvidence = issue.confidence_evidence
  const hasConfidence = confidenceScore != null

  const evidenceLabels = {
    ai: 'AI analysis',
    semgrep: 'Semgrep',
    bandit: 'Bandit',
    test_failure: 'Failed tests',
    git_history: 'Git history',
    dependency: 'Dependency analysis',
  }

  const confirmedEvidence = Object.entries(confidenceEvidence || {})
    .filter(([, confirmed]) => confirmed === true)
    .map(([source]) => evidenceLabels[source] || source)

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

          <section className="issue-section issue-confidence">
            <h4>Confidence Score</h4>

            {hasConfidence ? (
              <>
                <div className="confidence-header">
                  <span className="confidence-value">
                    {confidenceScore} / 100
                  </span>
                  <span className="confidence-level">
                    {confidenceLevel || 'Unclassified'} confidence
                  </span>
                </div>

                <div
                  className="confidence-progress"
                  role="progressbar"
                  aria-label="Confidence score"
                  aria-valuenow={confidenceScore}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="confidence-progress-fill"
                    style={{
                      width: `${Math.max(0, Math.min(100, confidenceScore))}%`,
                    }}
                  />
                </div>

                <p className="confidence-evidence">
                  <strong>Supporting evidence:</strong>{' '}
                  {confirmedEvidence.length > 0
                    ? confirmedEvidence.join(', ')
                    : 'No evidence sources recorded'}
                </p>

                <p className="confidence-note">
                  This score measures supporting evidence, not the
                  probability that a finding is correct.
                </p>
              </>
            ) : (
              <p className="confidence-unavailable">
                Not scored — this review may have been created before
                confidence scoring was introduced.
              </p>
            )}
          </section>

          {issue.line_number != null && (
            <span className="issue-line-reference">Line {issue.line_number}</span>
          )}
        </div>
      </div>
    </li>
  )
}

export default IssueCard
