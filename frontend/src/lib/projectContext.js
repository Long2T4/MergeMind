// These request limits mirror backend/app/models/schemas.py.
export function parseProjectSnapshot(text) {
  let files
  try { files = JSON.parse(text) } catch { throw new Error('Enter a valid JSON object mapping file paths to source text.') }
  if (!files || typeof files !== 'object' || Array.isArray(files)) {
    throw new Error('The snapshot must be a JSON object mapping file paths to source text.')
  }
  const entries = Object.entries(files)
  if (entries.length > 50) throw new Error('Include at most 50 project files.')
  const seen = new Set()
  let total = 0
  for (const [path, content] of entries) {
    validateProjectPath(path)
    const normalized = path.replaceAll('\\', '/').split('/').filter((part) => part && part !== '.').join('/')
    if (seen.has(normalized)) throw new Error(`Duplicate project path: ${normalized}`)
    seen.add(normalized)
    if (typeof content !== 'string') throw new Error('Every project file must contain source text.')
    total += content.length
  }
  if (total > 200000) throw new Error('Project files must total at most 200000 characters.')
  return files
}

export function validateProjectPath(path) {
  const normalized = path.replaceAll('\\', '/')
  const parts = normalized.split('/')
  if (!path || path.length > 240 || normalized.startsWith('/') || parts[0].includes(':')
      || parts.includes('..') || path.includes('\0')
      || !parts.some((part) => part && part !== '.')) {
    throw new Error('Use a relative project path of at most 240 characters, without parent traversal.')
  }
}

export function buildProjectContext({ filePath, sourceRoot, snapshotText }) {
  validateProjectPath(filePath)
  if (!/\.(py|js|jsx|ts|tsx|mjs|cjs)$/.test(filePath)) {
    throw new Error('Project context supports Python, JavaScript, and TypeScript files.')
  }
  if (sourceRoot) {
    validateProjectPath(sourceRoot)
    const path = filePath.replaceAll('\\', '/').split('/').filter((part) => part && part !== '.').join('/')
    const root = sourceRoot.replaceAll('\\', '/').split('/').filter((part) => part && part !== '.').join('/')
    if (!path.startsWith(`${root}/`)) throw new Error('The reviewed file must be inside the source root.')
  }
  return { file_path: filePath, source_root: sourceRoot, files: parseProjectSnapshot(snapshotText) }
}
