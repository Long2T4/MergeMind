import { useEffect, useState } from 'react'
import { accountRequest } from './auth'
import { STATUS_OPTIONS } from './statuses'

const STATUS_LABELS = Object.fromEntries(STATUS_OPTIONS)

export function Stage12Panel({ session, onLogout }) {
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState('projects')
  const [projects, setProjects] = useState([])
  const [selected, setSelected] = useState(localStorage.getItem('mergemind_active_project') || '')
  const [newName, setNewName] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [metrics, setMetrics] = useState(null)
  const [findings, setFindings] = useState([])
  const [reviewId, setReviewId] = useState('')
  const [busy, setBusy] = useState(false)
  const [updating, setUpdating] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function load(activeTab = tab) {
    setError(''); setNotice(''); setBusy(true)
    try {
      if (activeTab === 'projects') setProjects(await accountRequest('/projects'))
      if (activeTab === 'learning') setMetrics(await accountRequest('/learning'))
      if (activeTab === 'feedback') {
        const id = reviewId || (location.pathname.match(/\/reviews\/(\d+)/) || [])[1]
        if (id) { setFindings(await accountRequest(`/reviews/${id}/findings`)); setReviewId(String(id)) }
        else setFindings([])
      }
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }

  useEffect(() => { if (open) load(tab) }, [open, tab])

  async function addProject(event) {
    event.preventDefault(); setError(''); setBusy(true)
    try {
      const project = await accountRequest('/projects', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), description: newDescription.trim() || null }),
      })
      setProjects(list => [project, ...list]); setNewName(''); setNewDescription(''); setNotice('Project saved')
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }

  async function saveStatus(id, status) {
    setUpdating(id); setError(''); setNotice('')
    try {
      const result = await accountRequest(`/findings/${id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      setFindings(items => items.map(item => item.id === id ? { ...item, status: result.status } : item))
      setNotice('Feedback saved')
    } catch (e) { setError(e.message) }
    finally { setUpdating(null) }
  }

  const categoryEntries = Object.entries(metrics?.categories || {})
  const maxCount = Math.max(1, ...categoryEntries.map(([, count]) => count))
  return <>
    <div className="s12-controls">
      <button type="button" onClick={() => setOpen(value => !value)} aria-expanded={open} aria-label="Account and learning panel">Account & Learning</button>
      <button type="button" onClick={onLogout}>Log out</button>
    </div>
    {open && <aside className="s12-panel" aria-label="Stage 12 dashboard">
      <div className="s12-panel-header"><div><strong>Developer workspace</strong><small>{session.user.email}</small></div><button onClick={() => setOpen(false)} aria-label="Close panel">✕</button></div>
      <div className="s12-tabs" role="tablist">
        {['projects', 'feedback', 'learning'].map(name => <button key={name} role="tab" aria-selected={tab === name} className={tab === name ? 'active' : ''} onClick={() => setTab(name)}>{name}</button>)}
      </div>
      {error && <p className="s12-error" role="alert">{error}</p>}
      {notice && <p className="s12-notice" role="status">{notice}</p>}
      {busy && <p>Loading saved data…</p>}
      {tab === 'projects' && <section>
        <h2>My projects</h2>
        {!busy && !projects.length && <p>No projects yet. Create your first project below.</p>}
        {projects.map(project => <label key={project.id} className="s12-project">
          <input type="radio" checked={selected === String(project.id)} onChange={() => { setSelected(String(project.id)); localStorage.setItem('mergemind_active_project', String(project.id)); setNotice(`${project.name} selected`) }} />
          <span><strong>{project.name}</strong><small>{project.description || `Project #${project.id}`}</small></span>
        </label>)}
        <form className="s12-form" onSubmit={addProject}>
          <h3>Create project</h3>
          <input placeholder="Project name" required maxLength={255} value={newName} onChange={e => setNewName(e.target.value)} />
          <textarea placeholder="Optional description" maxLength={4000} value={newDescription} onChange={e => setNewDescription(e.target.value)} />
          <button disabled={busy || !newName.trim()}>Create project</button>
        </form>
        <p className="s12-muted">Selected project is saved in your browser. Existing review forms must also use this selection to attach new reviews.</p>
      </section>}
      {tab === 'feedback' && <section>
        <h2>Finding feedback</h2>
        <form className="s12-search" onSubmit={e => { e.preventDefault(); load('feedback') }}>
          <input type="number" min="1" placeholder="Review ID" value={reviewId} onChange={e => setReviewId(e.target.value)} />
          <button disabled={!reviewId}>Load review</button>
        </form>
        {!busy && !findings.length && <p>Open a review or enter its ID to view findings.</p>}
        {findings.map(finding => <div key={finding.id} className="s12-finding">
          <strong>{finding.title}</strong><small>{finding.category} · {finding.severity}</small>
          <select disabled={updating === finding.id} value={finding.status || 'open'} onChange={e => saveStatus(finding.id, e.target.value)} aria-label={`Status for ${finding.title}`}>
            {Object.entries(STATUS_LABELS).map(([value,label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>)}
      </section>}
      {tab === 'learning' && <section>
        <h2>Learning dashboard</h2>
        {metrics && <>
          <div className="s12-metrics">
            {[['Reviews', metrics.total_reviews], ['Issues', metrics.total_issues], ['Fixed (self-reported)', metrics.fixed_issues], ['False positives', metrics.false_positives]].map(([label,value]) => <div key={label}><small>{label}</small><strong>{value}</strong></div>)}
          </div>
          <h3>Finding outcomes</h3>
          <div className="s12-outcomes">{Object.entries(metrics.statuses).map(([key,value]) => <p key={key}>{STATUS_LABELS[key]}: <strong>{value}</strong></p>)}</div>
          <h3>Common categories</h3>
          {!categoryEntries.length && <p>No saved findings yet.</p>}
          {categoryEntries.map(([category,count]) => <div key={category} className="s12-bar-row"><span>{category} ({count})</span><div className="s12-track"><div style={{ width: `${100 * count/maxCount}%` }} /></div></div>)}
          <h3>Repeated across reviews</h3>
          {!metrics.repeated_categories.length && <p>No repeated categories yet.</p>}
          {metrics.repeated_categories.map(x => <p key={x.category}>{x.category}: {x.review_count} reviews</p>)}
          <p className="s12-muted">{metrics.trend_note}</p>
        </>}
      </section>}
    </aside>}
  </>
}
