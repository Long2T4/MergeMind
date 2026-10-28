import { Link } from 'react-router-dom'
import EmptyState from '../components/ui/EmptyState'

function NotFoundPage() {
  return (
    <div className="card">
      <EmptyState
        title="Page not found"
        action={<Link to="/" className="btn btn-secondary btn-sm">Go home</Link>}
      >
        That page doesn&apos;t exist.
      </EmptyState>
    </div>
  )
}

export default NotFoundPage
