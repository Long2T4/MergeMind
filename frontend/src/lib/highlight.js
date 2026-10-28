// Syntax highlighting for the languages MergeMind supports. Only these five
// grammars are bundled (highlight.js core + per-language imports).
import hljs from 'highlight.js/lib/core'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import python from 'highlight.js/lib/languages/python'

hljs.registerLanguage('python', python)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('java', java)
hljs.registerLanguage('c', c)
hljs.registerLanguage('cpp', cpp)

const SUPPORTED = new Set(['python', 'javascript', 'java', 'c', 'cpp'])

// Fenced-block hints the AI may use, mapped to our language values.
const ALIASES = { py: 'python', js: 'javascript', jsx: 'javascript', 'c++': 'cpp', cc: 'cpp' }

export function resolveLanguage(language) {
  const key = String(language || '').toLowerCase()
  const resolved = ALIASES[key] || key
  return SUPPORTED.has(resolved) ? resolved : null
}

export function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

// Returns HTML-escaped markup. highlight.js escapes the source itself, and
// unsupported languages fall back to plain escaped text.
export function highlightCode(code, language) {
  const text = code ?? ''
  const resolved = resolveLanguage(language)
  if (!resolved || !text) return escapeHtml(text)
  try {
    return hljs.highlight(text, { language: resolved, ignoreIllegals: true }).value
  } catch {
    return escapeHtml(text)
  }
}

// Highlights the whole snippet (so multi-line strings/comments stay correct),
// then splits it into per-line markup, closing and reopening any spans that
// cross a line break.
export function highlightLines(code, language) {
  const lines = highlightCode(code, language).split('\n')
  let open = []
  return lines.map((line) => {
    const prefix = open.join('')
    const tags = line.match(/<span[^>]*>|<\/span>/g) || []
    for (const tag of tags) {
      if (tag === '</span>') open.pop()
      else open.push(tag)
    }
    open = [...open]
    return prefix + line + '</span>'.repeat(open.length)
  })
}
