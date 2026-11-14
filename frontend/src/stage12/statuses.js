// Developer outcomes for a finding (review_issues.status). "Fixed" is the
// developer's own report, so it's always labeled self-reported.
export const STATUS_OPTIONS = [
  ['open', 'Open'],
  ['fixed', 'Fixed (self-reported)'],
  ['dismissed', 'Dismissed'],
  ['false_positive', 'False positive'],
]

const LABELS = Object.fromEntries(STATUS_OPTIONS)

export function statusLabel(status) {
  return LABELS[status] || LABELS.open
}
