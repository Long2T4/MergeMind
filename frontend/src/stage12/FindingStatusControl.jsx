import { useState } from 'react'
import { formatDateTime } from '../lib/format'
import { accountRequest } from './auth'
import { STATUS_OPTIONS } from './statuses'

// Stage 12: the developer's outcome for one finding, saved immediately.
export default function FindingStatusControl({ issueId, status, updatedAt }) {
  const [value, setValue] = useState(status || 'open')
  const [changedAt, setChangedAt] = useState(updatedAt || null)
  const [state, setState] = useState('idle')
  const [error, setError] = useState('')
  const id = `finding-status-${issueId}`

  async function change(event) {
    const next = event.target.value
    const previous = value
    setValue(next)
    setState('saving')
    setError('')
    try {
      const saved = await accountRequest(`/findings/${issueId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: next }),
      })
      setValue(saved.status)
      setChangedAt(saved.status_updated_at)
      setState('saved')
    } catch (err) {
      setValue(previous)
      setError(err.message || 'Could not save the outcome. Try again.')
      setState('error')
    }
  }

  return (
    <div className="finding-status">
      <label className="finding-status-label" htmlFor={id}>Your outcome</label>
      <select id={id} className="select finding-status-select" value={value} onChange={change}
        disabled={state === 'saving'}>
        {STATUS_OPTIONS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select>
      {state === 'saving' && <span role="status">Saving…</span>}
      {state === 'saved' && <span role="status" className="finding-status-saved">Saved</span>}
      {state === 'error' && <span role="alert" className="finding-status-error">{error}</span>}
      {changedAt && state !== 'saving' && (
        <span className="finding-status-time">Last changed {formatDateTime(changedAt)}</span>
      )}
    </div>
  )
}
