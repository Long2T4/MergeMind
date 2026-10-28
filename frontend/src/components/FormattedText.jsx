// Renders AI-generated text that may contain markdown-style code
// (```fenced blocks``` or `inline spans`) as proper code elements instead
// of showing raw backticks and collapsed newlines. Used by IssueCard for
// explanation, why_it_matters, and suggested_fix — all three come from the
// same AI response and can contain code the same way.
//
// Deliberately not a full markdown renderer: only backtick code is ever
// present in practice, so a small regex-based splitter is enough and avoids
// pulling in a markdown dependency. Code blocks are syntax-highlighted for
// the review's language (or the fence's language hint when it is supported).
import { resolveLanguage } from '../lib/highlight'
import CodeBlock from './ui/CodeBlock'

const FENCED_BLOCK_PATTERN = /```([\w+#-]*)\n?([\s\S]*?)```/g

function CodeSnippet({ code, language }) {
  return (
    <div className="formatted-code">
      <CodeBlock code={code} language={language} showLineNumbers={false} />
    </div>
  )
}

function renderWithInlineCode(text, keyPrefix, language) {
  // Split on `single-backtick` spans. The AI sometimes wraps multi-line code
  // in single backticks instead of a proper ``` fence — if that span
  // contains a newline, it needs block treatment, not inline <code>, or the
  // indentation/line breaks would still collapse.
  const parts = text.split(/(`[^`]+`)/g)
  const nodes = []
  let plainTextBuffer = []

  function flushPlainText(key) {
    if (plainTextBuffer.length > 0) {
      nodes.push(
        <p key={`text-${key}`} className="formatted-text">
          {plainTextBuffer}
        </p>,
      )
      plainTextBuffer = []
    }
  }

  parts.forEach((part, index) => {
    const isBacktickSpan = part.startsWith('`') && part.endsWith('`') && part.length > 1
    if (!isBacktickSpan) {
      if (part) plainTextBuffer.push(part)
      return
    }

    const codeContent = part.slice(1, -1)
    if (codeContent.includes('\n')) {
      flushPlainText(index)
      nodes.push(<CodeSnippet key={`block-${index}`} code={codeContent.trimEnd()} language={language} />)
    } else {
      plainTextBuffer.push(
        <code key={`${keyPrefix}-inline-${index}`} className="formatted-inline-code">
          {codeContent}
        </code>,
      )
    }
  })

  flushPlainText('end')
  return nodes
}

function FormattedText({ text, language }) {
  if (!text) return null

  const segments = []
  let lastIndex = 0
  let match

  FENCED_BLOCK_PATTERN.lastIndex = 0
  while ((match = FENCED_BLOCK_PATTERN.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) })
    }
    segments.push({ type: 'code', content: match[2].trimEnd(), hint: match[1] })
    lastIndex = FENCED_BLOCK_PATTERN.lastIndex
  }
  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) })
  }

  return (
    <>
      {segments.map((segment, index) => {
        if (segment.type === 'code') {
          const blockLanguage = resolveLanguage(segment.hint) || language
          return <CodeSnippet key={`block-${index}`} code={segment.content} language={blockLanguage} />
        }

        const trimmed = segment.content.trim()
        if (!trimmed) return null

        return renderWithInlineCode(trimmed, `text-${index}`, language)
      })}
    </>
  )
}

export default FormattedText
