// Stage 7 confidence score for a single finding.
const EVIDENCE_LABELS = {
  ai: 'AI analysis',
  semgrep: 'Semgrep',
  bandit: 'Bandit',
  test_failure: 'Failed tests',
  git_history: 'Git history',
  dependency: 'Dependency analysis',
}

export function confirmedEvidence(evidence) {
  return Object.entries(evidence || {})
    .filter(([, confirmed]) => confirmed === true)
    .map(([source]) => EVIDENCE_LABELS[source] || source)
}

function levelClass(level) {
  return ['low', 'medium', 'high'].includes(level) ? level : 'none'
}

// Compact pill for the collapsed issue header, so confidence is visible
// without expanding the card.
export function ConfidencePill({ issue }) {
  const score = issue.confidence_score
  if (score == null) {
    return <span className="confidence-pill level-none">Not scored</span>
  }
  return (
    <span className={`confidence-pill level-${levelClass(issue.confidence_level)}`}>
      <span aria-hidden="true">Confidence {score}</span>
      <span className="sr-only">Confidence score {score} out of 100</span>
    </span>
  )
}

function ConfidenceMeter({ issue }) {
  const confidenceScore = issue.confidence_score
  const confidenceLevel = issue.confidence_level
  const hasConfidence = confidenceScore != null
  const evidence = confirmedEvidence(issue.confidence_evidence)
  const width = hasConfidence ? Math.max(0, Math.min(100, confidenceScore)) : 0

  return (
    <section className="issue-confidence">
      <div className="issue-confidence-head">
        <h4 className="issue-label">Confidence Score</h4>
        {hasConfidence && (
          <span className={`confidence-level level-${levelClass(confidenceLevel)}`}>
            {confidenceLevel || 'Unclassified'} confidence
          </span>
        )}
      </div>

      {hasConfidence ? (
        <>
          <div className="confidence-row">
            <span className="confidence-value">{confidenceScore} / 100</span>
            <div
              className="confidence-progress"
              role="progressbar"
              aria-label="Confidence score"
              aria-valuenow={confidenceScore}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className={`confidence-progress-fill level-${levelClass(confidenceLevel)}`}
                style={{ width: `${width}%` }}
              />
            </div>
          </div>

          <p className="confidence-evidence">
            <strong>Supporting evidence:</strong>{' '}
            {evidence.length > 0 ? evidence.join(', ') : 'No evidence sources recorded'}
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
  )
}

export default ConfidenceMeter
