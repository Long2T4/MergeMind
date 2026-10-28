import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/layout/Icon'
import RecentReviewsTable from '../components/RecentReviewsTable'
import CodeBlock from '../components/ui/CodeBlock'
import ComingSoon from '../components/ui/ComingSoon'
import EmptyState from '../components/ui/EmptyState'
import ScoreRing from '../components/ui/ScoreRing'
import StatCard from '../components/ui/StatCard'
import { useProjects } from '../hooks/useProjects'
import { greetingFor } from '../lib/format'
import { getReviewHistory, getReviewHistoryStats } from '../services/api'
import './pages.css'

// Illustrative snippet for the "Paste your code" card (not a saved review).
const SAMPLE_CODE = `def login(username, password):
    query = f"SELECT * ... '{username}'"
    cursor.execute(query)`

function HeroStat({ stats, error }) {
  if (error) return <p className="muted">Review statistics are unavailable right now.</p>
  if (!stats) return <div className="skeleton hero-stat-skeleton" role="status" aria-label="Loading statistics" />
  if (stats.total_reviews === 0) {
    return (
      <div>
        <p className="hero-stat-label">No reviews yet</p>
        <p className="card-meta">Your completion rate appears after your first review.</p>
      </div>
    )
  }
  const rate = Math.round((stats.completed_reviews / stats.total_reviews) * 100)
  return (
    <>
      <ScoreRing value={rate} display={`${rate}%`} tone="accent" size={100} stroke={9} label={`Completion rate ${rate} percent`} />
      <div>
        <p className="hero-stat-label">Completion rate</p>
        <p className="hero-stat-value">{stats.completed_reviews} of {stats.total_reviews} completed</p>
        <p className="card-meta">Reviews that finished without an AI error</p>
      </div>
    </>
  )
}

function HomePage() {
  const [stats, setStats] = useState(null)
  const [statsError, setStatsError] = useState(false)
  const [recent, setRecent] = useState(null)
  const [recentError, setRecentError] = useState(false)
  const { byId } = useProjects()

  useEffect(() => {
    let active = true
    getReviewHistoryStats()
      .then((data) => { if (active) setStats(data) })
      .catch(() => { if (active) setStatsError(true) })
    getReviewHistory({ limit: 5, offset: 0 })
      .then((data) => { if (active) setRecent(data.items || []) })
      .catch(() => { if (active) setRecentError(true) })
    return () => { active = false }
  }, [])

  const averageIssues = stats && stats.completed_reviews > 0
    ? (stats.total_issues / stats.completed_reviews).toFixed(1)
    : null

  return (
    <div className="home">
      <section className="card home-hero">
        <div className="home-hero-text">
          <span className="accent-pill">AI code review for students</span>
          <h1 className="home-hero-title">
            {greetingFor()}
            <br />
            Let&apos;s ship cleaner code.
          </h1>
          <p className="home-hero-sub">
            AI feedback that explains the why, not just the what.
            <br />
            Every review makes your next commit better.
          </p>
          <p className="powered-by">
            <span>Powered by</span>
            <span className="tag">AI reasoning</span>
          </p>
        </div>
        <div className="home-hero-stat">
          <HeroStat stats={stats} error={statsError} />
        </div>
      </section>

      <div className="home-actions">
        <section className="card action-card" aria-labelledby="paste-title">
          <div className="action-card-top">
            <span className="icon-tile is-accent"><Icon name="code" /></span>
          </div>
          <div className="action-preview" aria-hidden="true">
            <CodeBlock code={SAMPLE_CODE} language="python" flaggedLines={[2]} />
          </div>
          <div className="action-card-bottom">
            <div>
              <h2 id="paste-title" className="card-title">Paste your code</h2>
              <p className="muted">Drop in a snippet or a file and get an AI review that explains each finding.</p>
            </div>
            <Link to="/reviews/new" className="btn btn-primary">
              Start review <Icon name="arrowRight" size={16} />
            </Link>
          </div>
        </section>

        <section className="card action-card" aria-labelledby="pr-title">
          <div className="action-card-top">
            <span className="icon-tile is-violet"><Icon name="pullRequest" /></span>
            <ComingSoon />
          </div>
          <div className="action-preview action-preview-empty">
            <p>Pull requests will appear here once GitHub integration is available.</p>
          </div>
          <div className="action-card-bottom">
            <div>
              <h2 id="pr-title" className="card-title">Review a pull request</h2>
              <p className="muted">GitHub integration isn&apos;t available yet. For now, paste the changed code into a new review.</p>
            </div>
          </div>
        </section>
      </div>

      {statsError ? (
        <div className="notice notice-error" role="alert">Could not load review statistics. Check the backend connection.</div>
      ) : (
        <div className="stat-grid" aria-label="Review statistics">
          <StatCard
            label="Total reviews"
            value={stats?.total_reviews}
            sub={stats ? `${stats.completed_reviews} completed` : 'Loading…'}
          />
          <StatCard label="Issues found" value={stats?.total_issues} tone="success">
            <Link to="/learning" className="stat-card-link">By category →</Link>
          </StatCard>
          <StatCard label="High severity" value={stats?.high_severity_issues} tone="high" sub="High-severity findings" />
          <StatCard label="Avg. issues per review" value={averageIssues ?? (stats ? '—' : undefined)} sub="Across completed reviews" />
        </div>
      )}

      <section className="card table-card recent-card" aria-labelledby="recent-title">
        <div className="table-card-header">
          <h2 id="recent-title" className="card-title">Recent reviews</h2>
          <Link to="/history" className="text-link">View all →</Link>
        </div>
        {recentError && (
          <div className="table-card-body">
            <div className="notice notice-error" role="alert">Could not load recent reviews. Check the backend connection.</div>
          </div>
        )}
        {!recentError && recent === null && <p className="table-card-body muted" role="status">Loading reviews...</p>}
        {!recentError && recent?.length === 0 && (
          <EmptyState
            title="No reviews yet"
            action={<Link to="/reviews/new" className="btn btn-primary btn-sm">Start your first review</Link>}
          >
            Paste some code to run your first review.
          </EmptyState>
        )}
        {!recentError && recent?.length > 0 && <RecentReviewsTable items={recent} projectsById={byId} />}
      </section>
    </div>
  )
}

export default HomePage
