import { useEffect, useState } from 'react'
import { accountRequest } from './auth'

export default function ProjectsWorkspace() {
  const [projects, setProjects] = useState([])
  const [selected, setSelected] = useState(localStorage.getItem('mergemind_active_project') || '')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
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
  function selectProject(project) {
    setSelected(String(project.id))
    localStorage.setItem('mergemind_active_project', String(project.id))
    setNotice(`${project.name} selected`)
  }
  return <section className="s12-embed">
    <h2>My projects</h2>
    <p className="s12-muted">Create a project and select it when submitting a review. Only your projects are available to your account.</p>
    {error && <p className="s12-error" role="alert">{error}</p>}
    {notice && <p className="s12-notice" role="status">{notice}</p>}
    {loading ? <p>Loading projects…</p> : !projects.length ? <p>No projects yet.</p> : <div className="s12-project-grid">
      {projects.map(project => <button key={project.id} type="button" className={selected === String(project.id) ? 'chosen' : ''} onClick={() => selectProject(project)}>
        <strong>{project.name}</strong><small>{project.description || `Project ${project.id}`}</small>
        <span>{selected === String(project.id) ? 'Selected' : 'Select project'}</span>
      </button>)}
    </div>}
    <form className="s12-form s12-create" onSubmit={submit}>
      <h3>Create a new project</h3>
      <input value={name} onChange={e => setName(e.target.value)} placeholder="Project name" required maxLength={255}/>
      <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Description (optional)" maxLength={4000}/>
      <button disabled={saving || !name.trim()}>{saving ? 'Creating…' : 'Create project'}</button>
    </form>
  </section>
}
