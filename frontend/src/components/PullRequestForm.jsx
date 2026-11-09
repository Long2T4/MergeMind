import { useEffect, useState } from 'react'
import { DEFAULT_PROJECT_ID } from '../constants/projects'
import { PR_URL_HINT, parsePullRequestUrl } from '../lib/pullRequest'
import Icon from './layout/Icon'

// Stage 11: review a public GitHub pull request by URL.
function PullRequestForm({ projects = [], initialValues = {}, onSubmit, isSubmitting, error }) {
  const [url, setUrl] = useState(initialValues.prUrl ?? '')
  const [sourceRoot, setSourceRoot] = useState(initialValues.sourceRoot ?? '')
  const [projectId, setProjectId] = useState(initialValues.projectId ?? DEFAULT_PROJECT_ID)
  const [urlError, setUrlError] = useState('')

  // Keep the selection valid once the real project list arrives.
  useEffect(() => {
    if (projects.length > 0 && !projects.some((project) => project.id === Number(projectId))) {
      setProjectId(projects[0].id)
    }
  }, [projects, projectId])

  const projectOptions = projects.length > 0
    ? projects
    : [{ id: DEFAULT_PROJECT_ID, name: 'Default project' }]

  function handleSubmit(event) {
    event.preventDefault()
    if (isSubmitting) return
    if (!parsePullRequestUrl(url)) {
      setUrlError(PR_URL_HINT)
      return
    }
    setUrlError('')
    onSubmit({ projectId: Number(projectId), prUrl: url.trim(), sourceRoot: sourceRoot.trim() })
  }

  return (
    <form className="new-review-grid" onSubmit={handleSubmit} aria-busy={isSubmitting} noValidate>
      <div className="new-review-main">
        <section className="card pr-form" aria-labelledby="pr-form-title">
          <h2 id="pr-form-title" className="card-title">Pull request</h2>
          <div className="field">
            <label className="field-label" htmlFor="pr-url">Pull request URL</label>
            <input
              id="pr-url"
              className="input mono"
              type="url"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              value={url}
              placeholder="https://github.com/owner/repository/pull/123"
              maxLength={300}
              disabled={isSubmitting}
              aria-invalid={urlError ? 'true' : undefined}
              aria-describedby={urlError ? 'pr-url-error' : 'pr-url-hint'}
              onChange={(event) => { setUrl(event.target.value); setUrlError('') }}
            />
            {urlError
              ? <p id="pr-url-error" className="field-error" role="alert">{urlError}</p>
              : <p id="pr-url-hint" className="options-text">Public repositories only.</p>}
          </div>
          <div className="new-review-fields">
            <div className="field">
              <label className="field-label" htmlFor="pr-project-select">Project</label>
              <select
                id="pr-project-select"
                className="select"
                value={projectId}
                onChange={(event) => setProjectId(Number(event.target.value))}
                disabled={isSubmitting}
              >
                {projectOptions.map((project) => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field-label" htmlFor="pr-source-root">Python source root (optional)</label>
              <input
                id="pr-source-root"
                className="input"
                value={sourceRoot}
                placeholder="backend"
                maxLength={240}
                disabled={isSubmitting}
                onChange={(event) => setSourceRoot(event.target.value)}
              />
            </div>
          </div>
        </section>
        {error && <div className="notice notice-error" role="alert">{error}</div>}
      </div>

      <aside className="new-review-aside">
        <section className="card options-card" aria-labelledby="pr-limits-title">
          <h2 id="pr-limits-title" className="card-title">What gets reviewed</h2>
          <ul className="pr-limits">
            <li>Pull requests with up to 30 changed files and 3,000 changed lines.</li>
            <li>The first 10 Python, JavaScript, TypeScript, Java, C and C++ files.</li>
            <li>Findings focus on the changed lines. A few serious ones elsewhere in a file are labeled "outside the diff".</li>
            <li>Removed, generated and binary files are skipped.</li>
            <li>Changed files and the files they import are sent to the AI provider. Nothing is posted to GitHub.</li>
          </ul>
        </section>

        <button type="submit" className="btn btn-primary btn-lg btn-block run-button" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Checking pull request…
            </>
          ) : (
            <>
              <Icon name="arrowRight" />
              Review pull request
            </>
          )}
        </button>
      </aside>
    </form>
  )
}

export default PullRequestForm
