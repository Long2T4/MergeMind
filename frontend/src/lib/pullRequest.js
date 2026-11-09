// Stage 11 helpers for GitHub pull request reviews.

// Same rule as backend/app/services/github_service.py (PR_URL_PATTERN). The
// backend checks again; this only gives faster feedback.
const PR_URL = /^https:\/\/github\.com\/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))\/([A-Za-z0-9._-]{1,100})\/pull\/([1-9][0-9]{0,9})\/?$/

export const PR_URL_HINT = 'Enter a pull request URL like https://github.com/owner/repository/pull/123'

export function parsePullRequestUrl(value) {
  const match = PR_URL.exec(String(value ?? '').trim())
  if (!match || match[2] === '.' || match[2] === '..') return null
  return { owner: match[1], repo: match[2], number: Number(match[3]) }
}

// The second line of a History or Home row: the pull request for PR reviews,
// otherwise the start of the submitted code.
export function reviewRowSubtitle(row) {
  if (row.pr_repo) return `${row.pr_repo}#${row.pr_number} · ${row.pr_title || ''}`.trim()
  return (row.code_preview || '').trim() || '(empty submission)'
}

// Why a file wasn't reviewed (pull_request_files.skip_reason).
export const SKIP_REASON_LABELS = {
  removed: 'removed file',
  generated: 'generated file',
  binary: 'binary file',
  too_large: 'too large',
  unsupported: 'unsupported file type',
  file_limit: 'over the 10-file limit',
}

export function fileStateLabel(file) {
  if (file.review_state === 'reviewed') return 'Reviewed'
  if (file.review_state === 'failed') return 'Review failed'
  if (file.review_state === 'pending') return 'Waiting'
  return `Skipped: ${SKIP_REASON_LABELS[file.skip_reason] || 'not reviewed'}`
}

// Files the background review works on: everything not skipped up front.
export function pullRequestProgress(pullRequest) {
  const files = pullRequest?.files || []
  const done = files.filter((file) => file.review_state === 'reviewed' || file.review_state === 'failed').length
  const pending = files.filter((file) => file.review_state === 'pending').length
  return { done, total: done + pending }
}

// New-file line number -> text, for the lines a patch shows (added and unchanged).
function patchLines(patch) {
  const lines = new Map()
  let current = null
  for (const row of String(patch ?? '').split('\n')) {
    const header = /^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(row)
    if (header) {
      current = Number(header[1])
    } else if (current !== null && !row.startsWith('\\') && !row.startsWith('-')) {
      lines.set(current, row.slice(1))
      current += 1
    }
  }
  return lines
}

// The "Flagged code" lines for a pull request finding, taken from the file's
// diff. null when the line isn't shown in the diff (for example, outside it).
export function diffContext(patch, lineNumber, radius = 1) {
  const lines = patchLines(patch)
  const line = Number(lineNumber)
  if (!Number.isInteger(line) || !lines.has(line)) return null
  let start = line
  while (start > line - radius && lines.has(start - 1)) start -= 1
  let end = line
  while (end < line + radius && lines.has(end + 1)) end += 1
  const code = []
  for (let number = start; number <= end; number += 1) code.push(lines.get(number))
  return { startLine: start, code: code.join('\n'), line }
}
