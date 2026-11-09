import { fileStateLabel, pullRequestProgress } from '../lib/pullRequest'
import Icon from './layout/Icon'
import CodeBlock from './ui/CodeBlock'

const GITHUB_PREFIX = 'https://github.com/'

// Stage 11: which pull request was reviewed, and progress while it runs.
export function PullRequestHeader({ review }) {
  const pr = review.pull_request
  const progress = pullRequestProgress(pr)
  const label = `${pr.owner}/${pr.repo}#${pr.number}`
  const safeUrl = typeof pr.html_url === 'string' && pr.html_url.startsWith(GITHUB_PREFIX)

  return (
    <section className="card pr-header" aria-labelledby="pr-title">
      <p className="eyebrow pr-eyebrow">
        <Icon name="pullRequest" size={14} />
        {safeUrl
          ? <a href={pr.html_url} target="_blank" rel="noopener noreferrer" className="text-link mono">{label}</a>
          : <span className="mono">{label}</span>}
      </p>
      <h2 id="pr-title" className="pr-title">{pr.title}</h2>
      <dl className="pr-meta">
        <div><dt>Author</dt><dd>{pr.author}</dd></div>
        <div><dt>Commit</dt><dd className="mono" title={pr.head_sha}>{pr.head_sha.slice(0, 7)}</dd></div>
        <div><dt>Files</dt><dd>{pr.changed_files_count}</dd></div>
        <div><dt>Lines</dt><dd className="mono">+{pr.additions} −{pr.deletions}</dd></div>
      </dl>
      {review.review_status === 'pending' && progress.total > 0 && (
        <div className="pr-progress" role="status">
          <span>Reviewing files: {progress.done} of {progress.total} done</span>
          <progress max={progress.total} value={progress.done} aria-hidden="true" />
        </div>
      )}
    </section>
  )
}

// Every changed file, whether it was reviewed, and its diff.
export function ChangedFiles({ pullRequest, issueCounts }) {
  return (
    <section className="card changed-files" aria-labelledby="changed-files-title">
      <h2 id="changed-files-title" className="card-title">Changed files</h2>
      <ul className="changed-file-list">
        {pullRequest.files.map((file) => {
          const count = issueCounts.get(file.path) || 0
          return (
            <li key={file.id} className={`changed-file state-${file.review_state}`}>
              <details>
                <summary>
                  <span className="changed-file-path mono">{file.path}</span>
                  <span className="changed-file-state">{fileStateLabel(file)}</span>
                  {count > 0 && <span className="changed-file-count">{count} {count === 1 ? 'finding' : 'findings'}</span>}
                  <span className="changed-file-lines mono">+{file.additions} −{file.deletions}</span>
                </summary>
                {file.patch
                  ? <CodeBlock code={file.patch} language="other" showLineNumbers={false} label={`Diff of ${file.path}`} />
                  : <p className="card-meta changed-file-nodiff">GitHub doesn't show a diff for this file.</p>}
              </details>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
