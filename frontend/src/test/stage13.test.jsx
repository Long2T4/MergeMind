import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { issue, mockApi, review } from './fixtures'
import { renderApp } from './utils'

vi.mock('../services/api')

beforeEach(() => {
  vi.resetAllMocks()
  mockApi(api)
})

async function statusCard(data) {
  api.getReviewHistoryDetail.mockResolvedValue(review(data))
  renderApp('/reviews/5')
  return screen.findByRole('region', { name: 'Static analysis' })
}

function rowText(card, scanner) {
  return within(card).getByText(scanner).closest('li').textContent
}

describe('Static analysis status on Review Results (Stage 13)', () => {
  it('says how many findings each scanner supports, or that it found none', async () => {
    const card = await statusCard({
      analysis_status: { semgrep: 'completed', bandit: 'completed' },
      issues: [
        issue({ id: 1, confidence_evidence: { ai: true, semgrep: true, bandit: true } }),
        issue({ id: 2, confidence_evidence: { semgrep: true } }),
      ],
    })
    expect(rowText(card, 'Semgrep')).toContain('Checked · supports 2 findings')
    expect(rowText(card, 'Bandit')).toContain('Checked · supports 1 finding')
  })

  it('tells "no issues found" apart from "not installed" and "failed"', async () => {
    const card = await statusCard({
      analysis_status: { semgrep: 'unavailable', bandit: 'failed' },
      issues: [issue({ confidence_evidence: { ai: true } })],
    })
    expect(rowText(card, 'Semgrep')).toContain('Not installed on this server')
    expect(rowText(card, 'Bandit')).toContain("Couldn't finish")
    expect(within(card).queryByText(/no issues found/)).not.toBeInTheDocument()
  })

  it('explains that only Python is scanned', async () => {
    const card = await statusCard({ analysis_status: { semgrep: 'not_run', bandit: 'not_run' }, programming_language: 'javascript' })
    expect(within(card).getAllByText('Not run · only Python is scanned')).toHaveLength(2)
  })

  it('marks older reviews as not recorded instead of clean', async () => {
    const card = await statusCard({ analysis_status: null })
    expect(card).toHaveTextContent('Not recorded')
  })

  it('is not shown until the review has completed', async () => {
    api.getReviewHistoryDetail.mockResolvedValue(review({ review_status: 'failed', analysis_status: null }))
    renderApp('/reviews/5')
    await screen.findByRole('heading', { level: 1 })
    expect(screen.queryByRole('region', { name: 'Static analysis' })).not.toBeInTheDocument()
  })
})
