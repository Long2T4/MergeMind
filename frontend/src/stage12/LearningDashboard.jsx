import { useEffect, useState } from 'react'
import { accountRequest } from './auth'
import { STATUS_OPTIONS } from './statuses'

// Stage 12: how you marked each saved finding, by category. The review and
// finding totals are on the learning profile above, so they aren't repeated.
export default function LearningDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    accountRequest('/learning').then(value => { if (active) setData(value) })
      .catch(e => { if (active) setError(e.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  if (loading) return <p className="notice" role="status">Loading finding outcomes…</p>
  if (error) return <div className="notice notice-error" role="alert">Could not load finding outcomes: {error}</div>
  const outcomes = Object.entries(data.category_outcomes || {})
  return (
    <section className="card learning-outcomes" aria-labelledby="outcomes-title">
      <div className="card-header">
        <h2 id="outcomes-title" className="card-title">Finding outcomes</h2>
        <span className="card-meta">All time</span>
      </div>
      <p className="muted">
        How you marked each saved finding. Fixed is what you reported, not a verified fix.
      </p>
      {!outcomes.length ? <p className="muted">No findings saved yet.</p> : (
        <div className="s12-table-wrap">
          <table className="s12-table">
            <caption className="sr-only">Finding outcomes by category</caption>
            <thead>
              <tr><th scope="col">Category</th>{STATUS_OPTIONS.map(([key, label]) => <th key={key} scope="col">{label}</th>)}</tr>
            </thead>
            <tbody>
              {outcomes.map(([category, counts]) => (
                <tr key={category}>
                  <th scope="row">{category}</th>
                  {STATUS_OPTIONS.map(([key]) => <td key={key}>{counts[key] ?? 0}</td>)}
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th scope="row">All categories</th>
                {STATUS_OPTIONS.map(([key]) => <td key={key}>{data.statuses?.[key] ?? 0}</td>)}
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  )
}
