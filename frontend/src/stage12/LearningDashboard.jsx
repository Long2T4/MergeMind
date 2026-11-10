import { useEffect, useState } from 'react'
import { accountRequest } from './auth'

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
  if (loading) return <section className="s12-embed">Loading your learning statistics…</section>
  if (error) return <section className="s12-embed s12-error" role="alert">{error}</section>
  const entries = Object.entries(data.categories)
  const high = Math.max(1, ...entries.map(([, v]) => v))
  return <section className="s12-embed">
    <h2>My learning progress</h2>
    <p className="s12-muted">Statistics from your own saved reviews and finding outcomes.</p>
    <div className="s12-metrics">
      {[['Reviews', data.total_reviews], ['PR reviews', data.pull_request_reviews], ['Fixed findings', data.fixed_issues], ['False positives', data.false_positives]].map(([name, value]) => <div key={name}><small>{name}</small><strong>{value}</strong></div>)}
    </div>
    <h3>Issue outcomes</h3>
    <div className="s12-outcomes">
      {Object.entries(data.statuses).map(([key,value]) => <p key={key}>{key.replace('_', ' ')}: <strong>{value}</strong></p>)}
    </div>
    <h3>Most common categories</h3>
    {!entries.length && <p>No findings saved yet.</p>}
    {entries.map(([category,count]) => <div className="s12-bar-row" key={category}><span>{category}: {count}</span><div className="s12-track"><div style={{ width: `${100*count/high}%` }}/></div></div>)}
    <h3>Repeated mistake categories</h3>
    {!data.repeated_categories.length && <p>No repeated categories across separate reviews yet.</p>}
    {data.repeated_categories.map(x => <p key={x.category}>{x.category}: {x.review_count} distinct reviews</p>)}
    <p className="s12-muted">{data.trend_note}</p>
  </section>
}
