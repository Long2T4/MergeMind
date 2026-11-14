// The project chosen on the Projects page is remembered in this browser and
// used as the default project for new reviews.
const SELECTED_PROJECT_KEY = 'mergemind_active_project'

export function getSelectedProjectId() {
  const value = Number(localStorage.getItem(SELECTED_PROJECT_KEY))
  return Number.isInteger(value) && value > 0 ? value : null
}

export function setSelectedProjectId(projectId) {
  localStorage.setItem(SELECTED_PROJECT_KEY, String(projectId))
}

export function projectLabel(project, projectId) {
  return project?.name || `Project #${projectId}`
}
