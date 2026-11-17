import { useState } from 'react'
import { accountRequest } from '../stage12/auth'
import CodeBlock from './ui/CodeBlock'

export default function BeginnerExplanation({ issueId, savedExplanation, language }) {
  const [generated, setGenerated] = useState(null)
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const explanation = savedExplanation || generated
  const panelId = `finding-explanation-${issueId}`

  async function openOrGenerate() {
    if (explanation) {
      setIsOpen((open) => !open)
      return
    }

    setError('')
    setIsLoading(true)
    try {
      const result = await accountRequest(`/findings/${issueId}/beginner-explanation`, { method: 'POST' })
      setGenerated(result)
      setIsOpen(true)
    } catch (err) {
      setError(err.message || 'Could not generate the explanation. Try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="finding-explanation">
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={isLoading}
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={openOrGenerate}
      >
        {error ? 'Retry explanation' : 'Explain like I’m new'}
      </button>
      {isLoading && <p role="status">Generating explanation…</p>}
      {error && <p role="alert" className="notice notice-error">{error}</p>}
      <div id={panelId} hidden={!isOpen}>
        {isOpen && explanation && (
          <section aria-label="Beginner explanation" className="finding-explanation-content">
            <div>
              <h4 className="issue-label">What’s wrong</h4>
              <p>{explanation.what_is_wrong}</p>
            </div>
            <div>
              <h4 className="issue-label">Why it matters</h4>
              <p>{explanation.why_it_matters}</p>
            </div>
            <div className="code-panel">
              <div className="code-panel-head">Example before</div>
              <CodeBlock code={explanation.before} language={language} />
            </div>
            <div className="code-panel is-fix">
              <div className="code-panel-head">Example after</div>
              <CodeBlock code={explanation.after} language={language} />
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
