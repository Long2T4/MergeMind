import { useDeferredValue, useMemo, useRef } from 'react'
import { countLines } from '../../lib/code'
import { pluralize } from '../../lib/format'
import { highlightCode } from '../../lib/highlight'

// A plain <textarea> layered over a highlighted <pre>, so typing, pasting,
// undo and accessibility all stay native while the code is coloured.
function CodeEditor({
  id, value, onChange, language, fileName, actions, footerHint, onSubmitShortcut, disabled, placeholder,
}) {
  const highlightRef = useRef(null)
  const gutterRef = useRef(null)
  const lineCount = Math.max(1, countLines(value))
  // Highlighting can lag behind typing on large files without blocking input.
  const deferredValue = useDeferredValue(value)
  const highlighted = useMemo(() => highlightCode(deferredValue, language), [deferredValue, language])

  function syncScroll(event) {
    const { scrollTop, scrollLeft } = event.currentTarget
    if (highlightRef.current) {
      highlightRef.current.scrollTop = scrollTop
      highlightRef.current.scrollLeft = scrollLeft
    }
    if (gutterRef.current) gutterRef.current.scrollTop = scrollTop
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      event.preventDefault()
      onSubmitShortcut?.()
    }
  }

  return (
    <div className={`code-editor ${disabled ? 'is-disabled' : ''}`}>
      <div className="code-editor-bar">
        <span className="code-editor-dots" aria-hidden="true"><span /><span /><span /></span>
        <span className="code-editor-tab">{fileName}</span>
        {actions && <div className="code-editor-actions">{actions}</div>}
      </div>

      <div className="code-editor-body">
        <div className="code-editor-gutter" ref={gutterRef} aria-hidden="true">
          {Array.from({ length: lineCount }, (_, index) => <span key={index}>{index + 1}</span>)}
        </div>
        <div className="code-editor-surface">
          <pre className="code-editor-highlight" ref={highlightRef} aria-hidden="true">
            {/* Escaped by highlight.js; the trailing newline keeps the last line's height. */}
            <code dangerouslySetInnerHTML={{ __html: `${highlighted}\n` }} />
          </pre>
          <textarea
            id={id}
            className="code-editor-input"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onScroll={syncScroll}
            onKeyDown={handleKeyDown}
            spellCheck={false}
            autoCapitalize="off"
            autoComplete="off"
            autoCorrect="off"
            wrap="off"
            disabled={disabled}
            placeholder={placeholder}
          />
        </div>
      </div>

      <div className="code-editor-footer">
        <span>{footerHint}</span>
        <span className="mono">
          {pluralize(countLines(value), 'line')} · {pluralize(value.length, 'char')}
        </span>
      </div>
    </div>
  )
}

export default CodeEditor
