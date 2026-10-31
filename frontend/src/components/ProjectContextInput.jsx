function ProjectContextInput({ value, onChange, disabled, error, uploadError, onUpload, reading }) {
  function update(key, next) { onChange({ ...value, [key]: next }) }
  return (
    <section className="card project-context" aria-labelledby="project-context-title">
      <h2 id="project-context-title" className="card-title">Project context</h2>
      <label className="context-toggle">
        <input type="checkbox" checked={value.enabled} disabled={disabled}
          onChange={(event) => update('enabled', event.target.checked)} />
        Include related project files
      </label>
      <p className="options-text">Supply project files so the AI can understand direct imports. Only relevant files are selected.</p>
      {value.enabled && (
        <div className="context-fields">
          <div className="field">
            <label className="field-label" htmlFor="review-file-path">Reviewed file path</label>
            <input id="review-file-path" className="input" value={value.filePath} placeholder="src/routes.py"
              maxLength={240} disabled={disabled} onChange={(event) => update('filePath', event.target.value)} />
          </div>
          <div className="field">
            <label className="field-label" htmlFor="source-root">Python source root (optional)</label>
            <input id="source-root" className="input" value={value.sourceRoot} placeholder="backend"
              maxLength={240} disabled={disabled} onChange={(event) => update('sourceRoot', event.target.value)} />
          </div>
          <div className="field">
            <label className="field-label" htmlFor="project-snapshot">Project files JSON</label>
            <textarea id="project-snapshot" className="input context-json" value={value.snapshotText}
              spellCheck={false} rows={7} disabled={disabled || reading}
              onChange={(event) => update('snapshotText', event.target.value)}
              placeholder={'{"src/models.py": "class User: ..."}'} />
          </div>
          <label className="field-label" htmlFor="snapshot-upload">Upload project JSON</label>
          <input id="snapshot-upload" type="file" accept=".json,application/json" disabled={disabled || reading}
            onChange={onUpload} />
          {reading && <p role="status">Reading project files…</p>}
          <p className="options-text">Map relative file paths to source text. Up to 50 files and 200,000 characters; the AI receives at most 8 imported files and 24,000 context characters. These files are sent to the AI provider. They are not saved with the review; attach them again when retrying.</p>
          {(error || uploadError) && <p className="field-error" role="alert">{uploadError || error}</p>}
        </div>
      )}
    </section>
  )
}
export default ProjectContextInput
