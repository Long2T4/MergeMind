import { afterEach, describe, expect, it, vi } from 'vitest'
import { createCodeReview } from '../services/api'

afterEach(() => vi.unstubAllGlobals())
describe('Context request serialization', () => {
  it('serializes optional context using the backend contract', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 42 }) })
    vi.stubGlobal('fetch', fetch)
    const context = { file_path: 'app.py', source_root: '', files: { 'models.py': 'class User: pass' } }
    await createCodeReview({ projectId: 1, submittedCode: 'import models', programmingLanguage: 'python', projectContext: context })
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ project_id: 1, submitted_code: 'import models',
      programming_language: 'python', project_context: context })
  })
  it('omits context for legacy requests and propagates readable validation errors', async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ detail: 'Project paths must be relative' }) })
    vi.stubGlobal('fetch', fetch)
    await expect(createCodeReview({ projectId: 1, submittedCode: 'x', programmingLanguage: 'python' }))
      .rejects.toMatchObject({ message: 'Project paths must be relative', validation: true })
    expect(JSON.parse(fetch.mock.calls[0][1].body)).not.toHaveProperty('project_context')
  })
})
