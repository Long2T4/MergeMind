import { fireEvent, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { issue, mockApi, review } from './fixtures'
import { renderApp } from './utils'

vi.mock('../services/api')

beforeEach(() => {
  vi.resetAllMocks()
  mockApi(api)
})

describe('Review results', () => {
  it('loads the review by id, independent of any review list', async () => {
    renderApp('/reviews/5')

    expect(await screen.findByRole('heading', { level: 1, name: 'Login App' })).toBeInTheDocument()
    expect(api.getReviewHistoryDetail).toHaveBeenCalledWith('5')
    expect(api.getCodeReviews).not.toHaveBeenCalled()
    expect(api.getReviewHistory).not.toHaveBeenCalled()
    expect(screen.getByRole('link', { name: /Back to history/ })).toHaveAttribute('href', '/history')
  })

  it('only uses in-app paths for the back link', async () => {
    renderApp({ pathname: '/reviews/5', state: { from: '//evil.example', fromLabel: 'Back somewhere' } })
    const back = await screen.findByRole('link', { name: /Back to history/ })
    expect(back).toHaveAttribute('href', '/history')

    await screen.findByRole('heading', { level: 1, name: 'Login App' })
  })

  it('shows the Stage 8 merge risk score prominently', async () => {
    renderApp('/reviews/5')

    expect(await screen.findByRole('img', { name: 'Merge risk 72 out of 100, high' })).toBeInTheDocument()
    expect(screen.getByText('72/100')).toBeInTheDocument()
    expect(screen.getByText('HIGH RISK')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Overall merge risk' })).toHaveAttribute('aria-valuenow', '72')
    expect(screen.getByText('60/100')).toBeInTheDocument()
  })

  it('shows Stage 7 confidence on collapsed cards and in the details', async () => {
    api.getReviewHistoryDetail.mockResolvedValue(review({
      issues: [
        issue(),
        issue({
          id: 12, title: 'Magic number', severity: 'low', category: 'code_quality', line_number: 3,
          confidence_score: null, confidence_level: null, confidence_evidence: null,
        }),
      ],
    }))
    renderApp('/reviews/5')

    expect(await screen.findByText('Confidence 20')).toBeInTheDocument()
    expect(screen.getByText('Not scored')).toBeInTheDocument()

    // The first finding opens by default.
    expect(screen.getByText('20 / 100')).toBeVisible()
    expect(screen.getByText('low confidence')).toBeVisible()
    expect(screen.getByRole('progressbar', { name: 'Confidence score' })).toHaveAttribute('aria-valuenow', '20')
    expect(screen.getByText('Supporting evidence:').closest('p')).toHaveTextContent('Supporting evidence: AI analysis')

    const second = screen.getByRole('button', { name: /^Low Magic number/ })
    expect(second).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(second)
    expect(second).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/Not scored — this review may have been created before confidence scoring/)).toBeVisible()
  })

  it('opens a finding from "Where the issues are" without losing the back target', async () => {
    api.getReviewHistoryDetail.mockResolvedValue(review({
      issues: [issue(), issue({ id: 12, title: 'Magic number', severity: 'low', line_number: 3 })],
    }))
    renderApp({ pathname: '/reviews/5', state: { from: '/history?q=x', fromLabel: 'Back to history' } })

    const card = await screen.findByRole('button', { name: /^Low Magic number/ })
    expect(card).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(screen.getByRole('button', { name: /line 3 Magic number/ }))
    expect(card).toHaveAttribute('aria-expanded', 'true')
    expect(card).toHaveFocus()
    expect(screen.getByRole('link', { name: /Back to history/ })).toHaveAttribute('href', '/history?q=x')
  })

  it('filters findings by category', async () => {
    api.getReviewHistoryDetail.mockResolvedValue(review({
      issues: [issue(), issue({ id: 12, title: 'Magic number', category: 'code_quality', severity: 'low' })],
    }))
    renderApp('/reviews/5')

    fireEvent.click(await screen.findByRole('button', { name: 'Code quality · 1' }))
    expect(screen.queryByRole('button', { name: /^High SQL injection risk/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Low Magic number/ })).toBeInTheDocument()
  })

  it('handles a missing review', async () => {
    api.getReviewHistoryDetail.mockRejectedValue(Object.assign(new Error('not found'), { status: 404 }))
    renderApp('/reviews/99')
    expect(await screen.findByText('Review #99 could not be found.')).toBeInTheDocument()
  })

  it('retries after an API error', async () => {
    api.getReviewHistoryDetail.mockRejectedValueOnce(new Error('offline'))
    renderApp('/reviews/5')

    fireEvent.click(await screen.findByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Login App' })).toBeInTheDocument()
    expect(api.getReviewHistoryDetail).toHaveBeenCalledTimes(2)
  })

  it('shows a failed review with a retry link and no risk score', async () => {
    api.getReviewHistoryDetail.mockResolvedValue(review({
      review_status: 'failed', issues: [], risk_score: null, risk_level: null, risk_breakdown: null,
    }))
    renderApp('/reviews/5')

    expect(await screen.findByText('Risk assessment unavailable because the review is not completed.')).toBeInTheDocument()
    expect(screen.getByText('No issues to show for this review.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Retry review/ })).toHaveAttribute('href', '/reviews/new')
  })
})
