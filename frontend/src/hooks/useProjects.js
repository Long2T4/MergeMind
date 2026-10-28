import { useEffect, useMemo, useState } from 'react'
import { getProjects } from '../services/api'

// Loads the existing projects list (GET /projects/) so pages can show
// project names instead of bare ids. Failure is non-fatal.
export function useProjects() {
  const [state, setState] = useState({ projects: [], loaded: false, error: false })

  useEffect(() => {
    let active = true
    getProjects()
      .then((projects) => { if (active) setState({ projects: projects || [], loaded: true, error: false }) })
      .catch(() => { if (active) setState({ projects: [], loaded: true, error: true }) })
    return () => { active = false }
  }, [])

  const byId = useMemo(
    () => new Map(state.projects.map((project) => [project.id, project])),
    [state.projects],
  )

  return { ...state, byId }
}
