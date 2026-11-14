import { useEffect, useState } from 'react'
import { getSelectedProjectId, setSelectedProjectId } from '../constants/projects'
import { accountRequest } from './auth'

export default function ProjectsWorkspace() {
  const [projects, setProjects] = useState([])
  const [selected, setSelected] = useState(String(getSelectedProjectId() ?? ''))
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [renaming, setRenaming] = useState(null)
  const [newName, setNewName] = useState('')
  useEffect(() => {
    let live = true
    accountRequest('/projects').then(data => { if (live) setProjects(data) })
      .catch(e => { if (live) setError(e.message) })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [])
  async function submit(e) {
    e.preventDefault(); setSaving(true); setError(''); setNotice('')
    try {
      const project = await accountRequest('/projects', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), description: description.trim() || null }),
      })
      setProjects(current => [project, ...current]); setName(''); setDescription(''); setNotice('Project created')
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }
  function startRename(project) {
    setRenaming(project.id); setNewName(project.name); setError(''); setNotice('')
  }
  async function saveRename(e) {
    e.preventDefault(); setSaving(true); setError(''); setNotice('')
    try {
      const updated = await accountRequest(`/projects/${renaming}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim() }),
      })
      setProjects(current => current.map(p => (p.id === updated.id ? updated : p)))
      setRenaming(null); setNotice('Project renamed')
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }
  function selectProject(project) {
    setSelected(String(project.id))
    setSelectedProjectId(project.id)
    setNotice(`New reviews will use ${project.name}`)
  }
  return <section className="s12-embed">
    <h2>My projects</h2>
    <p className="s12-muted">New reviews use the selected project; you can still choose another one on the New Review page. Only you can see your projects.</p>
    {error && <p className="s12-error" role="alert">{error}</p>}
    {notice && <p className="s12-notice" role="status">{notice}</p>}
    {loading ? <p>Loading projects…</p> : !projects.length ? <p>No projects yet. Create your first project below, then start a review.</p> : <div className="s12-project-grid">
      {projects.map(project => <div key={project.id} className="s12-project-card">
        {renaming === project.id ? (
          <form className="s12-rename" onSubmit={saveRename}>
            <label htmlFor={`rename-${project.id}`}>New name for {project.name}</label>
            <input id={`rename-${project.id}`} value={newName} onChange={e => setNewName(e.target.value)} maxLength={255} required />
            <div className="s12-rename-actions">
              <button type="submit" disabled={saving || !newName.trim()}>{saving ? 'Saving…' : 'Save name'}</button>
              <button type="button" className="s12-rename-button" onClick={() => setRenaming(null)}>Cancel</button>
            </div>
          </form>
        ) : <>
          <button type="button" className={selected === String(project.id) ? 'chosen' : ''} onClick={() => selectProject(project)}>
            <strong>{project.name}</strong><small>{project.description || `Project ${project.id}`}</small>
            <span>{selected === String(project.id) ? 'Selected' : 'Select project'}</span>
          </button>
          <button type="button" className="s12-rename-button" aria-label={`Rename ${project.name}`} onClick={() => startRename(project)}>Rename</button>
        </>}
      </div>)}
    </div>}
    <form className="s12-form s12-create" onSubmit={submit}>
      <h3>Create a new project</h3>
      <input value={name} onChange={e => setName(e.target.value)} placeholder="Project name" required maxLength={255}/>
      <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Description (optional)" maxLength={4000}/>
      <button className="btn btn-primary btn-sm" disabled={saving || !name.trim()}>{saving ? 'Creating…' : 'Create project'}</button>
    </form>
  </section>
}
