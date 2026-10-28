import { useProjects } from '../hooks/useProjects'
import EmptyState from '../components/ui/EmptyState'
import { formatShortDate } from '../lib/format'
import './pages.css'

// Read-only list from the existing GET /projects/ endpoint.
function ProjectsPage() {
  const { projects, loaded, error } = useProjects()

  return (
    <div className="projects-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Projects</h1>
          <p className="page-subtitle">Projects your reviews are attached to.</p>
        </div>
      </div>

      {!loaded && <p className="notice" role="status">Loading projects…</p>}
      {loaded && error && (
        <div className="notice notice-error" role="alert">Could not load projects. Check the backend connection.</div>
      )}
      {loaded && !error && projects.length === 0 && (
        <div className="card">
          <EmptyState title="No projects yet">
            New reviews are saved to the default project.
          </EmptyState>
        </div>
      )}
      {loaded && !error && projects.length > 0 && (
        <ul className="project-grid">
          {projects.map((project) => (
            <li key={project.id} className="card project-card">
              <p className="eyebrow">Project #{project.id}</p>
              <h2 className="card-title">{project.name}</h2>
              <p className="muted">{project.description || 'No description.'}</p>
              <p className="card-meta">Created {formatShortDate(project.created_at)}</p>
            </li>
          ))}
        </ul>
      )}

      <p className="page-footnote">Creating and editing projects from the app isn&apos;t available yet.</p>
    </div>
  )
}

export default ProjectsPage
