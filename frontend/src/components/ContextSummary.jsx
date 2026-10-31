function ContextSummary({ summary, failed }) {
  if (!summary) return null
  return (
    <section className="card context-summary" aria-labelledby="context-summary-title">
      <h2 id="context-summary-title" className="card-title">{failed ? 'Selected project context' : 'Project context used'}</h2>
      <p>Reviewed <code>{summary.file_path}</code> with {summary.selected_files.length} related file{summary.selected_files.length === 1 ? '' : 's'} ({summary.total_chars.toLocaleString()} characters).</p>
      {failed && <p>The AI review failed; selected files do not mean a review was completed.</p>}
      {summary.selected_files.length > 0 && <ul>{summary.selected_files.map((path) => <li key={path}><code>{path}</code></li>)}</ul>}
      {summary.omitted_files.length > 0 && <p>Excluded by context limits: {summary.omitted_files.join(', ')}.</p>}
      {summary.unresolved_imports.length > 0 && <p>Imports not resolved from supplied files: {summary.unresolved_imports.join(', ')}. These may be external packages.</p>}
      <p className="options-text">Context details are available for this submission only. Project files are not saved in review history.</p>
    </section>
  )
}
export default ContextSummary
