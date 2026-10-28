import { Link } from 'react-router-dom'
import Icon from '../components/layout/Icon'
import ReviewHistory from '../components/ReviewHistory'

function HistoryPage() {
  return (
    <div className="history-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Review history</h1>
          <p className="page-subtitle">Every review you&apos;ve run, and how your findings break down.</p>
        </div>
        <Link to="/reviews/new" className="btn btn-primary">
          <Icon name="plus" size={16} />
          New review
        </Link>
      </div>
      <ReviewHistory />
    </div>
  )
}

export default HistoryPage
