import { useMemo } from 'react'
import { highlightLines } from '../../lib/highlight'

// Read-only, syntax-highlighted code with optional line numbers and
// flagged-line highlighting.
function CodeBlock({ code, language, startLine = 1, flaggedLines = [], showLineNumbers = true, label }) {
  const lines = useMemo(() => highlightLines(code, language), [code, language])
  const flagged = new Set(flaggedLines)

  return (
    <pre
      className={`code-block ${showLineNumbers ? '' : 'no-numbers'}`}
      // Scrollable regions must be reachable by keyboard.
      tabIndex={0}
      role={label ? 'region' : undefined}
      aria-label={label}
    >
      <code>
        {lines.map((html, index) => {
          const lineNumber = startLine + index
          return (
            <span key={lineNumber} className={`code-line ${flagged.has(lineNumber) ? 'is-flagged' : ''}`}>
              {showLineNumbers && <span className="code-line-number" aria-hidden="true">{lineNumber}</span>}
              {/* highlight.js output is already HTML-escaped (see lib/highlight). */}
              <span className="code-line-content" dangerouslySetInnerHTML={{ __html: html || ' ' }} />
            </span>
          )
        })}
      </code>
    </pre>
  )
}

export default CodeBlock
