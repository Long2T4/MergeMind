import { Link } from 'react-router-dom'
import { LANGUAGE_SHORT } from '../constants/languages'
import { projectLabel } from '../constants/projects'
import { formatDateTime, pluralize } from '../lib/format'
import Icon from './layout/Icon'
import SeverityBar from './ui/SeverityBar'
import StatusBadge from './ui/StatusBadge'

const FROM_HOME = { from: '/', fromLabel: 'Back to home' }

// Dashboard table of the latest reviews (lightweight history summaries).
function RecentReviewsTable({ items, projectsById }) {
  return (
    <table className="data-table recent-table stack-table">
      <caption className="sr-only">Most recent code reviews</caption>
      <thead>
        <tr>
          <th scope="col">Project</th>
          <th scope="col">Status</th>
          <th scope="col">Issues</th>
          <th scope="col">Date</th>
          <th scope="col"><span className="sr-only">Open</span></th>
        </tr>
      </thead>
      <tbody>
        {items.map((review) => (
          <tr key={review.id}>
            <td data-label="Project">
              <div className="cell-project">
                <span className="lang-chip" aria-hidden="true">
                  {LANGUAGE_SHORT[review.programming_language] ?? '··'}
                </span>
                <div className="cell-project-text">
                  <Link to={`/reviews/${review.id}`} state={FROM_HOME} className="cell-project-name">
                    {projectLabel(projectsById.get(review.project_id), review.project_id)}
                  </Link>
                  <code className="cell-project-sub">
                    Review #{review.id} · {review.code_preview?.trim() || '(empty submission)'}
                  </code>
                </div>
              </div>
            </td>
            <td data-label="Status"><StatusBadge status={review.review_status} /></td>
            <td data-label="Issues">
              {review.review_status === 'completed' ? (
                <SeverityBar
                  high={review.high_severity_count ?? 0}
                  medium={review.medium_severity_count ?? 0}
                  low={review.low_severity_count ?? 0}
                  label={pluralize(review.issue_count, 'issue')}
                />
              ) : (
                <span className="muted">n/a</span>
              )}
            </td>
            <td data-label="Date" className="cell-date">
              <time dateTime={review.created_at}>{formatDateTime(review.created_at)}</time>
            </td>
            <td className="cell-arrow">
              <Link to={`/reviews/${review.id}`} state={FROM_HOME} tabIndex={-1} aria-hidden="true">
                <Icon name="arrowRight" size={16} />
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default RecentReviewsTable
