import ProjectsWorkspace from '../stage12/ProjectsWorkspace'
import './pages.css'

// Stage 12: the signed-in user's projects, with project creation.
function ProjectsPage() {
  return (
    <div className="projects-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Projects</h1>
          <p className="page-subtitle">Projects your reviews are attached to.</p>
        </div>
      </div>
      <ProjectsWorkspace />
    </div>
  )
}

export default ProjectsPage
