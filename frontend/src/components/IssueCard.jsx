import { useState } from 'react'
import { codeContext } from '../lib/code'
import CategoryBadge from './CategoryBadge'
import ConfidenceMeter, { ConfidencePill, confirmedEvidence } from './ConfidenceMeter'
import FormattedText from './FormattedText'
import Icon from './layout/Icon'
import SeverityBadge from './SeverityBadge'
import CodeBlock from './ui/CodeBlock'

function IssueCard({ issue, code, language, defaultExpanded = false }) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  // Older issues saved before the title/why_it_matters fields existed may
  // have title: null — fall back to a generic label rather than showing blank.
  const displayTitle = issue.title || 'Code review finding'
  const severity = String(issue.severity || '').toLowerCase()
  const bodyId = `issue-${issue.id}-details`
  const context = codeContext(code, issue.line_number)
  const evidence = confirmedEvidence(issue.confidence_evidence)

  return (
    <li id={`issue-${issue.id}`} className={`issue-card severity-border-${severity} ${isExpanded ? 'is-open' : ''}`}>
      <h3 className="issue-card-heading">
        <button
          type="button"
          className="issue-card-header"
          onClick={() => setIsExpanded((prev) => !prev)}
          aria-expanded={isExpanded}
          aria-controls={bodyId}
        >
          <SeverityBadge severity={issue.severity} />
          <span className="issue-card-title">{displayTitle}</span>
          <CategoryBadge category={issue.category} />
          <span className="issue-card-meta">
            <ConfidencePill issue={issue} />
            {issue.line_number != null && (
              <span className="issue-card-line">line {issue.line_number}</span>
            )}
            <Icon name="chevronDown" size={16} className="issue-card-chevron" />
          </span>
        </button>
      </h3>

      <div className="issue-card-body" id={bodyId} hidden={!isExpanded}>
        <div className="issue-explain">
          <section>
            <h4 className="issue-label">What's wrong</h4>
            <FormattedText text={issue.explanation} language={language} />
          </section>

          {issue.why_it_matters && (
            <section>
              <h4 className="issue-label">Why it matters</h4>
              <FormattedText text={issue.why_it_matters} language={language} />
            </section>
          )}
        </div>

        {context && (
          <div className="code-panel">
            <div className="code-panel-head">
              <span>Flagged code</span>
              <span className="mono">line {context.line}</span>
            </div>
            <CodeBlock
              code={context.code}
              language={language}
              startLine={context.startLine}
              flaggedLines={[context.line]}
            />
          </div>
        )}

        {issue.suggested_fix && (
          <div className="code-panel is-fix">
            <div className="code-panel-head">
              <span>Suggested fix</span>
              {evidence.length > 0 && <span className="mono">{evidence.join(' + ')}</span>}
            </div>
            <div className="code-panel-body">
              <FormattedText text={issue.suggested_fix} language={language} />
            </div>
          </div>
        )}

        <ConfidenceMeter issue={issue} />
      </div>
    </li>
  )
}

export default IssueCard
