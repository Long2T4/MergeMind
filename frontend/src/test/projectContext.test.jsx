import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { buildProjectContext, parseProjectSnapshot } from '../lib/projectContext'
import { mockApi, review } from './fixtures'
import { renderApp } from './utils'

vi.mock('../services/api')
beforeEach(() => { vi.resetAllMocks(); mockApi(api) })

function enableContext() {
  fireEvent.click(screen.getByLabelText('Include related project files'))
  fireEvent.change(screen.getByLabelText('Reviewed file path'), { target: { value: 'src/review.py' } })
  fireEvent.change(screen.getByLabelText('Paste your code'), { target: { value: 'from src.models import User' } })
}

describe('Project-aware review flow', () => {
  it('blocks a failed upload until corrected and supports TypeScript review context', async () => {
    renderApp('/reviews/new')
    await screen.findByRole('button', { name: /Run review/ })
    enableContext()
    const file = new File(['{}'], 'project.json')
    file.text = vi.fn().mockRejectedValue(new Error('read error'))
    fireEvent.change(screen.getByLabelText('Upload project JSON'), { target: { files: [file] } })
    expect(await screen.findByText('Could not read the project snapshot. Choose it again.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Run review/ })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Reviewed file path'), { target: { value: 'src/review.ts' } })
    fireEvent.change(screen.getByLabelText('Language'), { target: { value: 'typescript' } })
    fireEvent.change(screen.getByLabelText('Project files JSON'), { target: { value: '{"src/models.ts":"export type User = string"}' } })
    fireEvent.click(screen.getByRole('button', { name: /Run review/ }))
    await waitFor(() => expect(api.createCodeReview).toHaveBeenCalled())
    expect(api.createCodeReview.mock.calls[0][0].programmingLanguage).toBe('typescript')
    expect(api.createCodeReview.mock.calls[0][0].projectContext.file_path).toBe('src/review.ts')
  })

  it('passes the supplied snapshot to the API and shows selection diagnostics', async () => {
    const summary = { file_path: 'src/review.py', selected_files: ['src/models.py'], total_chars: 16,
      unresolved_imports: ['external'], omitted_files: ['src/huge.py'] }
    api.createCodeReview.mockResolvedValue(review({ id: 42, context_summary: summary }))
    renderApp('/reviews/new')
    await screen.findByRole('button', { name: /Run review/ })
    enableContext()
    fireEvent.change(screen.getByLabelText('Project files JSON'), { target: { value: '{"src/models.py":"class User: pass"}' } })
    fireEvent.click(screen.getByRole('button', { name: /Run review/ }))
    await waitFor(() => expect(api.createCodeReview).toHaveBeenCalledWith({
      projectId: 1, submittedCode: 'from src.models import User', programmingLanguage: 'python',
      projectContext: { file_path: 'src/review.py', source_root: '', files: { 'src/models.py': 'class User: pass' } },
    }))
    expect(await screen.findByRole('heading', { name: 'Project context used' })).toBeInTheDocument()
    expect(screen.getByText('src/models.py')).toBeInTheDocument()
    expect(screen.getByText(/Excluded by context limits: src\/huge.py/)).toBeInTheDocument()
    expect(screen.getByText(/These may be external packages/)).toBeInTheDocument()
  })

  it('blocks invalid JSON and allows ordinary submission after disabling context', async () => {
    renderApp('/reviews/new')
    await screen.findByRole('button', { name: /Run review/ })
    enableContext()
    fireEvent.change(screen.getByLabelText('Project files JSON'), { target: { value: '{bad' } })
    expect(screen.getByRole('alert')).toHaveTextContent('valid JSON')
    expect(screen.getByRole('button', { name: /Run review/ })).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Include related project files'))
    fireEvent.click(screen.getByRole('button', { name: /Run review/ }))
    await waitFor(() => expect(api.createCodeReview).toHaveBeenCalledWith({
      projectId: 1, submittedCode: 'from src.models import User', programmingLanguage: 'python',
    }))
  })

  it('reads a JSON upload and submits its source text', async () => {
    renderApp('/reviews/new')
    await screen.findByRole('button', { name: /Run review/ })
    enableContext()
    const file = new File(['{}'], 'project.json', { type: 'application/json' })
    file.text = vi.fn().mockResolvedValue('{"src/models.py":"class User: pass"}')
    fireEvent.change(screen.getByLabelText('Upload project JSON'), { target: { files: [file] } })
    await waitFor(() => expect(screen.getByLabelText('Project files JSON')).toHaveValue('{"src/models.py":"class User: pass"}'))
    fireEvent.click(screen.getByRole('button', { name: /Run review/ }))
    await waitFor(() => expect(api.createCodeReview).toHaveBeenCalled())
    expect(api.createCodeReview.mock.calls[0][0].projectContext.files['src/models.py']).toBe('class User: pass')
  })

  it('preserves the snapshot and displays backend validation errors', async () => {
    api.createCodeReview.mockRejectedValue(Object.assign(new Error('Review input exceeds the prompt limit'), { validation: true }))
    renderApp('/reviews/new')
    await screen.findByRole('button', { name: /Run review/ })
    enableContext()
    fireEvent.click(screen.getByRole('button', { name: /Run review/ }))
    expect(await screen.findByText('Review input exceeds the prompt limit')).toBeInTheDocument()
    expect(screen.getByLabelText('Reviewed file path')).toHaveValue('src/review.py')
  })

  it('labels selection honestly when the AI review failed', async () => {
    api.createCodeReview.mockResolvedValue(review({ id: 42, context_summary: {
      file_path: 'src/review.py', selected_files: [], total_chars: 0, unresolved_imports: [], omitted_files: [],
    } }))
    api.getReviewHistoryDetail.mockResolvedValue(review({ id: 42, review_status: 'failed', issues: [] }))
    renderApp('/reviews/new')
    await screen.findByRole('button', { name: /Run review/ })
    enableContext()
    fireEvent.click(screen.getByRole('button', { name: /Run review/ }))
    expect(await screen.findByRole('heading', { name: 'Selected project context' })).toBeInTheDocument()
    expect(screen.getByText(/The AI review failed; selected files/)).toBeInTheDocument()
  })
})

describe('Snapshot validation', () => {
  it.each(['[]', 'null', '{"a.py":3}', '{"../bad.py":"x"}', '{"a.py":"x","./a.py":"y"}',
    JSON.stringify(Object.fromEntries(Array.from({ length: 51 }, (_, i) => [`m${i}.py`, '']))),
    JSON.stringify({ 'large.py': 'x'.repeat(200001) }),
  ])('rejects invalid snapshot %#', (text) => {
    expect(() => parseProjectSnapshot(text)).toThrow()
  })
  it('requires the reviewed file to be inside the source root', () => {
    expect(() => buildProjectContext({ filePath: 'src/review.py', sourceRoot: 'backend', snapshotText: '{}' })).toThrow(/inside/)
  })
})
