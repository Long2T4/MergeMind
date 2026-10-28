// Finding categories produced by the AI review service (Stage 4).
export const CATEGORY_LABELS = {
  security: 'Security',
  testing: 'Testing',
  error_handling: 'Error handling',
  input_validation: 'Input validation',
  database: 'Database',
  performance: 'Performance',
  code_quality: 'Code quality',
  logic: 'Logic',
}

// Generic, static guidance per category. This is general advice, not
// something derived from the user's own findings.
export const CATEGORY_GUIDANCE = {
  security:
    'Treat every external value as untrusted. Use parameterised queries, encode output, and keep secrets out of source code.',
  testing:
    'Add a small test for each behaviour you change, including edge cases and failure paths, so regressions show up before review.',
  error_handling:
    'Catch only the errors you can handle, give users a clear message, and log enough detail to debug without exposing internals.',
  input_validation:
    'Validate type, length and format where data enters your code, then let the rest of the code assume it is clean.',
  database:
    'Use parameterised queries, close connections reliably, and avoid running one query per loop iteration when a single query will do.',
  performance:
    'Measure before optimising. Watch for repeated work inside loops and data structures that make lookups slow.',
  code_quality:
    'Prefer clear names, small functions and named constants over magic numbers, so the next reader understands the intent quickly.',
  logic:
    'Walk through edge cases such as empty input, off-by-one boundaries and unexpected types before trusting the happy path.',
}

export function normalizeCategory(category) {
  const value = String(category ?? '').trim().toLowerCase().replace(/[\s-]+/g, '_')
  return value || 'uncategorized'
}

export function categoryLabel(category) {
  const key = normalizeCategory(category)
  if (CATEGORY_LABELS[key]) return CATEGORY_LABELS[key]
  if (key === 'uncategorized') return 'Uncategorized'
  return key.replace(/_/g, ' ').replace(/^\w/, (letter) => letter.toUpperCase())
}
