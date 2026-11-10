import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { accountRequest } from './auth'

const OUTCOMES = ['open', 'fixed', 'dismissed', 'false_positive']
export default function ReviewFeedback() {
  const params = useParams()
  const reviewId = params.reviewId || params.id
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(null)
  const [notice, setNotice] = useState('')
  useEffect(() => {
    if (!reviewId) { setLoading(false); return }
    let active = true
    accountRequest(`/reviews/${reviewId}/findings`)
      .then(data => { if (active) setItems(data) })
      .catch(err => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [reviewId])
  async function update(id, status) {
    setSaving(id); setError(''); setNotice('')
    try {
      const saved = await accountRequest(`/findings/${id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      setItems(current => current.map(item => item.id === id ? { ...item, status: saved.status } : item))
      setNotice('Finding status saved')
    } catch (err) { setError(err.message) }
    finally { setSaving(null) }
  }
  return <section className="s12-embed">
    <h2>Developer feedback</h2>
    <p className="s12-muted">Mark the outcome of each finding. Your changes are saved to the database and counted in Learning.</p>
    {loading && <p>Loading findings…</p>}
    {error && <p role="alert" className="s12-error">{error}</p>}
    {notice && <p role="status" className="s12-notice">{notice}</p>}
    {!loading && !items.length && !error && <p>This review has no findings yet.</p>}
    {items.map(issue => <div key={issue.id} className="s12-finding">
      <strong>{issue.title}</strong><small>{issue.category} · {issue.severity}</small>
      <label>Finding status
        <select value={issue.status} disabled={saving === issue.id} onChange={e => update(issue.id, e.target.value)}>
          {OUTCOMES.map(value => <option key={value} value={value}>{value.replace('_', ' ')}</option>)}
        </select>
      </label>
    </div>)}
  </section>
}
