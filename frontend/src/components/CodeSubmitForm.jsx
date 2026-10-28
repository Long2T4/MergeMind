import { useEffect, useRef, useState } from 'react'
import { CATEGORY_LABELS } from '../constants/categories'
import {
  LANGUAGE_EXTENSIONS, LANGUAGE_LABELS, LANGUAGES, languageFromFileName,
} from '../constants/languages'
import { DEFAULT_PROJECT_ID } from '../constants/projects'
import Icon from './layout/Icon'
import CodeEditor from './ui/CodeEditor'
import ComingSoon from './ui/ComingSoon'

const MAX_UPLOAD_BYTES = 200 * 1024
const IS_MAC = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || '')
const SHORTCUT = IS_MAC ? '⌘↵' : 'Ctrl ↵'

const ANALYZERS = [
  { name: 'AI reasoning', available: true },
  { name: 'Semgrep', available: false },
  { name: 'Bandit', available: false },
  { name: 'ESLint', available: false },
]

function CodeSubmitForm({ projects = [], initialValues = {}, onSubmit, isSubmitting, error }) {
  const [code, setCode] = useState(initialValues.code ?? '')
  const [language, setLanguage] = useState(initialValues.language ?? 'python')
  const [projectId, setProjectId] = useState(initialValues.projectId ?? DEFAULT_PROJECT_ID)
  const [fileName, setFileName] = useState(null)
  const [uploadError, setUploadError] = useState('')
  const fileInputRef = useRef(null)

  // Keep the selection valid once the real project list arrives.
  useEffect(() => {
    if (projects.length > 0 && !projects.some((project) => project.id === Number(projectId))) {
      setProjectId(projects[0].id)
    }
  }, [projects, projectId])

  const projectOptions = projects.length > 0
    ? projects
    : [{ id: DEFAULT_PROJECT_ID, name: 'Default project' }]
  const canSubmit = code.trim().length > 0 && !isSubmitting

  function submit() {
    if (!canSubmit) return
    onSubmit({ code, language, projectId: Number(projectId) })
  }

  function handleSubmit(event) {
    event.preventDefault()
    submit()
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (file.size > MAX_UPLOAD_BYTES) {
      setUploadError('That file is larger than 200 KB. Paste a smaller snippet instead.')
      return
    }
    // Read in the browser only: the file's text goes into the editor and is
    // submitted the same way as pasted code.
    file.text()
      .then((text) => {
        setCode(text)
        setFileName(file.name)
        setUploadError('')
        const detected = languageFromFileName(file.name)
        if (detected) setLanguage(detected)
      })
      .catch(() => setUploadError('Could not read that file.'))
  }

  return (
    <form className="new-review-grid" onSubmit={handleSubmit} aria-busy={isSubmitting}>
      <div className="new-review-main">
        <div className="new-review-fields">
          <div className="field">
            <label className="field-label" htmlFor="project-select">Project</label>
            <select
              id="project-select"
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
            <label className="field-label" htmlFor="language-select">Language</label>
            <select
              id="language-select"
              className="select"
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
              disabled={isSubmitting}
            >
              {LANGUAGES.map((lang) => (
                <option key={lang} value={lang}>{LANGUAGE_LABELS[lang]}</option>
              ))}
            </select>
          </div>
        </div>

        <label className="sr-only" htmlFor="code-input">Paste your code</label>
        <CodeEditor
          id="code-input"
          value={code}
          onChange={(value) => { setCode(value); if (!value) setFileName(null) }}
          language={language}
          fileName={fileName || `snippet.${LANGUAGE_EXTENSIONS[language] || 'txt'}`}
          placeholder="Paste your code here..."
          disabled={isSubmitting}
          onSubmitShortcut={submit}
          footerHint={fileName ? `Loaded ${fileName}` : `Press ${SHORTCUT} to run the review`}
          actions={(
            <>
              <input
                ref={fileInputRef}
                type="file"
                hidden
                accept=".py,.js,.jsx,.mjs,.cjs,.java,.c,.h,.cpp,.cc,.cxx,.hpp,.hh,.txt"
                onChange={handleFileChange}
              />
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={isSubmitting}
              >
                <Icon name="upload" size={16} />
                Upload file
              </button>
            </>
          )}
        />

        {uploadError && <p className="field-error" role="alert">{uploadError}</p>}
        {error && <div className="notice notice-error" role="alert">{error}</div>}
      </div>

      <aside className="new-review-aside">
        <section className="card options-card" aria-labelledby="options-title">
          <div className="card-header">
            <h2 id="options-title" className="card-title">Review depth</h2>
            <ComingSoon />
          </div>
          <p className="options-text">
            Every review currently runs one full AI pass with explanations. Choosing a quicker or
            deeper review isn't available yet.
          </p>
        </section>

        <section className="card options-card" aria-labelledby="focus-title">
          <div className="card-header">
            <h2 id="focus-title" className="card-title">Focus on</h2>
            <ComingSoon />
          </div>
          <p className="options-text">Every review checks all of these categories:</p>
          <ul className="focus-tags">
            {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
              <li key={key} className="focus-tag">{label}</li>
            ))}
          </ul>
        </section>

        <section className="card options-card" aria-labelledby="analyzers-title">
          <h2 id="analyzers-title" className="card-title">Analyzers</h2>
          <ul className="analyzer-list">
            {ANALYZERS.map((analyzer) => (
              <li key={analyzer.name}>
                <span className="mono">{analyzer.name}</span>
                {analyzer.available
                  ? <span className="analyzer-on">● on</span>
                  : <span className="analyzer-off">○ not available yet</span>}
              </li>
            ))}
          </ul>
        </section>

        <button type="submit" className="btn btn-primary btn-lg btn-block run-button" disabled={!canSubmit}>
          {isSubmitting ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Running review…
            </>
          ) : (
            <>
              <Icon name="arrowRight" />
              Run review
              <kbd className="kbd" aria-hidden="true">{SHORTCUT}</kbd>
            </>
          )}
        </button>
        {isSubmitting && (
          <p className="run-hint" role="status">
            The AI review can take a little while. Results open as soon as it finishes.
          </p>
        )}
      </aside>
    </form>
  )
}

export default CodeSubmitForm
