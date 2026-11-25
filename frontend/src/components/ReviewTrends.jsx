import { useEffect, useMemo, useState } from 'react'
import { useProjects } from '../hooks/useProjects'
import { getReviewTrends } from '../services/api'
import './ReviewTrends.css'

const TIME_OPTIONS = [
  ['7', '7 days'],
  ['30', '30 days'],
  ['90', '90 days'],
  ['all', 'All time'],
]

const SEVERITY_SERIES = [
  { key: 'high', label: 'High', color: 'var(--high)' },
  { key: 'medium', label: 'Medium', color: 'var(--medium)' },
  { key: 'low', label: 'Low', color: 'var(--low)' },
]

const CATEGORY_SERIES = [
  { key: 'security', label: 'Security', color: 'var(--high)' },
  { key: 'logic', label: 'Logic', color: 'var(--violet)' },
  { key: 'performance', label: 'Performance', color: 'var(--medium)' },
  { key: 'code_quality', label: 'Code Quality', color: 'var(--accent)' },
  { key: 'other', label: 'Other categories', color: 'var(--low)' },
]

const SVG_W = 760
const SVG_H = 252
const LEFT = 42
const TOP = 15
const RIGHT = 14
const BOTTOM = 42
const PLOT_W = SVG_W - LEFT - RIGHT
const PLOT_H = SVG_H - TOP - BOTTOM

function dateLabel(iso, granularity) {
  if (!iso) return ''
  const date = new Date(`${iso}T12:00:00Z`)
  const options = granularity === 'month'
    ? { month: 'short', year: '2-digit', timeZone: 'UTC' }
    : { month: 'short', day: 'numeric', timeZone: 'UTC' }
  return date.toLocaleDateString('en-US', options)
}

function TrendChart({ heading, points, series, granularity }) {
  const maxCount = Math.max(1, ...points.flatMap((p) => series.map((s) => p[s.key] || 0)))
  const yMax = Math.max(4, Math.ceil(maxCount / 4) * 4)
  const x = (i) => LEFT + (points.length <= 1 ? PLOT_W / 2 : (i / (points.length - 1)) * PLOT_W)
  const y = (value) => TOP + PLOT_H * (1 - (value || 0) / yMax)
  const ticks = [...new Set([0, 1, 2, 3, 4].map((i) => Math.round((points.length - 1) * i / 4)))]

  return (
    <section className="card rt-chart-card" aria-label={heading}>
      <div className="rt-chart-header">
        <h3 className="card-title">{heading}</h3>
        <div className="rt-legend" aria-label={`${heading} legend`}>
          {series.map((s) => (
            <span key={s.key} className="rt-legend-item">
              <span className="rt-legend-dot" style={{ backgroundColor: s.color }} aria-hidden="true" />
              {s.label}
            </span>
          ))}
        </div>
      </div>
      <div className="rt-chart-scroll">
        <svg className="rt-chart-svg" viewBox={`0 0 ${SVG_W} ${SVG_H}`} role="img"
          aria-label={`${heading} over time. Exact values are available in the data table below.`}>
          <title>{heading} by date, based on saved review issues</title>
          {[0, 1, 2, 3, 4].map((i) => {
            const count = (i * yMax) / 4
            const ordinate = y(count)
            return (
              <g key={i}>
                <line x1={LEFT} x2={SVG_W - RIGHT} y1={ordinate} y2={ordinate} className="rt-grid-line" />
                <text x={LEFT - 10} y={ordinate + 4} textAnchor="end" className="rt-axis-text">{count}</text>
              </g>
            )
          })}
          {series.map((s) => (
            <g key={s.key}>
              <polyline
                fill="none" stroke={s.color} strokeWidth="2.8" strokeLinejoin="round" strokeLinecap="round"
                points={points.map((p, i) => `${x(i)},${y(p[s.key])}`).join(' ')}
                vectorEffect="non-scaling-stroke"
              />
              {points.map((p, i) => (
                <circle key={`${s.key}-${p.date}`} cx={x(i)} cy={y(p[s.key])}
                  r={points.length > 32 ? 2 : 3.5} fill={s.color}>
                  <title>{`${dateLabel(p.date, granularity)}: ${s.label}: ${p[s.key] || 0}`}</title>
                </circle>
              ))}
            </g>
          ))}
          {ticks.map((i) => (
            <text key={i} x={x(i)} y={SVG_H - 13} textAnchor="middle" className="rt-axis-text">
              {dateLabel(points[i]?.date, granularity)}
            </text>
          ))}
        </svg>
      </div>
      <details className="rt-data-details">
        <summary>View exact chart values</summary>
        <div className="rt-table-scroll">
          <table className="data-table rt-data-table">
            <thead>
              <tr><th scope="col">Period</th>{series.map((s) => <th scope="col" key={s.key}>{s.label}</th>)}</tr>
            </thead>
            <tbody>
              {points.map((p) => (
                <tr key={p.date}>
                  <td>{dateLabel(p.date, granularity)}</td>
                  {series.map((s) => <td key={s.key}>{p[s.key] || 0}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  )
}

function Stat({ label, value, note, className = '' }) {
  return (
    <div className={`card stat-card rt-stat ${className}`}>
      <span className="stat-card-label">{label}</span>
      <strong className="stat-card-value">{value}</strong>
      {note && <span className="stat-card-sub">{note}</span>}
    </div>
  )
}

export default function ReviewTrends() {
  const [days, setDays] = useState('30')
  const [projectId, setProjectId] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const { projects } = useProjects()

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    setResult(null)
    getReviewTrends({ days, projectId, signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setResult(data) })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setError(`Could not load review trends: ${err.message}`)
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [days, projectId, attempt])

  const summary = result?.summary
  const points = result?.points || []
  const categories = useMemo(() => (
    points.some((p) => p.other > 0) ? CATEGORY_SERIES : CATEGORY_SERIES.filter((s) => s.key !== 'other')
  ), [points])
  const severity = useMemo(() => (
    points.some((p) => p.unclassified > 0)
      ? [...SEVERITY_SERIES, { key: 'unclassified', label: 'Unclassified', color: 'var(--text-faint)' }]
      : SEVERITY_SERIES
  ), [points])

  return (
    <section className="rt-root" aria-labelledby="rt-heading">
      <div className="rt-header">
        <div>
          <span className="eyebrow">Stage 6.1 · Analytics</span>
          <h2 id="rt-heading" className="rt-title">Review trends</h2>
          <p className="muted">Analyze saved findings across every review, not just the current history page.</p>
        </div>
        <div className="rt-controls">
          <label className="field" htmlFor="rt-days">
            <span className="field-label">Time range</span>
            <select id="rt-days" className="select" value={days} onChange={(e) => setDays(e.target.value)}>
              {TIME_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label className="field" htmlFor="rt-project">
            <span className="field-label">Project</span>
            <select id="rt-project" className="select" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">All projects</option>
              {projects.map((p) => <option key={p.id} value={String(p.id)}>{p.name || `Project #${p.id}`}</option>)}
            </select>
          </label>
        </div>
      </div>

      {loading && <div className="card rt-message" role="status">Loading trends from saved reviews…</div>}
      {error && !loading && (
        <div className="card rt-message" role="alert">
          <p>{error}</p>
          <button className="btn btn-secondary btn-sm" type="button" onClick={() => setAttempt((n) => n + 1)}>Try again</button>
        </div>
      )}
      {!loading && !error && summary && (
        <>
          <div className="rt-stats">
            <Stat label="Total reviews" value={summary.total_reviews.toLocaleString()} note="All statuses" />
            <Stat label="Total issues" value={summary.total_issues.toLocaleString()} note="Saved findings" />
            <Stat label="Avg. issues per review" value={summary.average_issues_per_review.toFixed(1)} note="Issues ÷ all reviews" />
            <Stat label="High-severity issues" value={summary.high_severity_issues.toLocaleString()} note="Needs attention" className="rt-stat-high" />
          </div>
          {summary.total_issues === 0 ? (
            <div className="card rt-message">{summary.total_reviews === 0
              ? 'No saved reviews match this time range and project.'
              : 'Reviews were found, but none contain saved issues for these filters.'}</div>
          ) : (
            <div className="rt-charts">
              <TrendChart heading="Severity trends" points={points} series={severity} granularity={result.granularity} />
              <TrendChart heading="Category trends" points={points} series={categories} granularity={result.granularity} />
            </div>
          )}
          <p className="rt-footnote">
            Data comes from existing code_reviews and review_issues records. Dates use UTC; the 90-day view groups by week
            and all-time groups by month. Other categories include Testing, Error Handling, Input Validation, and Database.
          </p>
        </>
      )}
    </section>
  )
}
