// No project management UI exists yet, so submissions default to this
// project (the same fixed id the app has always used).
export const DEFAULT_PROJECT_ID = 1

export function projectLabel(project, projectId) {
  return project?.name || `Project #${projectId}`
}
