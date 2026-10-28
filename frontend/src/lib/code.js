export function splitLines(code) {
  return String(code ?? '').replace(/\r\n?/g, '\n').split('\n')
}

export function countLines(code) {
  if (!code) return 0
  return splitLines(code).length
}

// The lines around a reported line number, for the "Flagged code" panel.
// Returns null when the line number doesn't point inside the submission.
export function codeContext(code, lineNumber, radius = 1) {
  const lines = splitLines(code)
  const line = Number(lineNumber)
  if (!Number.isInteger(line) || line < 1 || line > lines.length) return null
  const start = Math.max(1, line - radius)
  const end = Math.min(lines.length, line + radius)
  return { startLine: start, code: lines.slice(start - 1, end).join('\n'), line }
}
