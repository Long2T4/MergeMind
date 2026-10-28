import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { issue, mockApi, review } from './fixtures'
import { renderApp } from './utils'

vi.mock('../services/api')

beforeEach(() => {
  vi.resetAllMocks()
  mockApi(api)
})

describe('Home dashboard', () => {
  it('shows real statistics and recent reviews, with no invented metrics', async () => {
    renderApp('/')

    expect(await screen.findByText('10 of 12 completed')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Completion rate 83 percent' })).toBeInTheDocument()
    expect(screen.getByText('25')).toBeInTheDocument()
    expect(screen.getByText('2.5')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Login App' })).toHaveAttribute('href', '/reviews/1')
    expect(api.getReviewHistory).toHaveBeenCalledWith({ limit: 5, offset: 0 })

    expect(screen.queryByText(/fix rate/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/false positives/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/streak/i)).not.toBeInTheDocument()
    expect(screen.getByText('Coming soon')).toBeInTheDocument()
  })

  it('shows empty states when there are no reviews', async () => {
    api.getReviewHistoryStats.mockResolvedValue({ total_reviews: 0, completed_reviews: 0, total_issues: 0, high_severity_issues: 0 })
    api.getReviewHistory.mockResolvedValue({ items: [], total: 0 })
    renderApp('/')

    expect(await screen.findAllByText('No reviews yet')).toHaveLength(2)
    expect(screen.getByRole('link', { name: 'Start your first review' })).toHaveAttribute('href', '/reviews/new')
  })

  it('reports statistics errors', async () => {
    api.getReviewHistoryStats.mockRejectedValue(new Error('offline'))
    renderApp('/')
    expect(await screen.findByText('Could not load review statistics. Check the backend connection.')).toBeInTheDocument()
  })
})

describe('New review', () => {
  it('submits the existing request format and opens the results', async () => {
    renderApp('/reviews/new')
    const runButton = await screen.findByRole('button', { name: /Run review/ })
    expect(runButton).toBeDisabled()

    fireEvent.change(screen.getByLabelText('Language'), { target: { value: 'cpp' } })
    fireEvent.change(screen.getByLabelText('Paste your code'), { target: { value: 'int main() {}' } })
    expect(screen.getByText('snippet.cpp')).toBeInTheDocument()
    fireEvent.click(runButton)

    await waitFor(() => expect(api.createCodeReview).toHaveBeenCalledWith({
      projectId: 1, submittedCode: 'int main() {}', programmingLanguage: 'cpp',
    }))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/reviews/42'))
  })

  it('keeps the code and shows an error when submission fails', async () => {
    api.createCodeReview.mockRejectedValue(new Error('offline'))
    renderApp('/reviews/new')

    const editor = await screen.findByLabelText('Paste your code')
    fireEvent.change(editor, { target: { value: 'print(1)' } })
    fireEvent.click(screen.getByRole('button', { name: /Run review/ }))

    expect(await screen.findByText('Failed to submit code. Please try again.')).toBeInTheDocument()
    expect(editor).toHaveValue('print(1)')
  })

  it('prefills the original code when retrying a review', async () => {
    renderApp({ pathname: '/reviews/new', state: { retryReviewId: 5 } })

    expect(await screen.findByText(/Retrying review #5/)).toBeInTheDocument()
    expect(screen.getByLabelText('Paste your code')).toHaveValue(review().submitted_code)
    expect(api.getReviewHistoryDetail).toHaveBeenCalledWith(5)
  })

  it('starts empty when leaving a retry for a fresh New Review', async () => {
    renderApp({ pathname: '/reviews/new', state: { retryReviewId: 5 } })
    expect(await screen.findByLabelText('Paste your code')).toHaveValue(review().submitted_code)

    fireEvent.click(screen.getByRole('link', { name: 'New Review' }))
    await waitFor(() => expect(screen.getByLabelText('Paste your code')).toHaveValue(''))
    expect(screen.queryByText(/Retrying review/)).not.toBeInTheDocument()
  })

  it('labels unsupported options instead of faking them', async () => {
    renderApp('/reviews/new')
    await screen.findByRole('button', { name: /Run review/ })
    expect(screen.getAllByText('○ not available yet')).toHaveLength(3)
    expect(screen.getByText('● on')).toBeInTheDocument()
    expect(screen.getAllByText('Coming soon').length).toBeGreaterThan(0)
  })
})

describe('Learning profile', () => {
  const reviews = [
    review({ id: 5, created_at: '2026-10-09T14:15:00', issues: [issue({ id: 1 }), issue({ id: 2, category: 'logic', severity: 'low' })] }),
    review({ id: 6, created_at: '2026-10-12T10:00:00', issues: [issue({ id: 3 })] }),
  ]

  it('labels data coverage and avoids invented progress metrics', async () => {
    api.getCodeReviews.mockResolvedValue(reviews)
    api.getReviewHistoryStats.mockResolvedValue({ total_reviews: 2, completed_reviews: 2, total_issues: 3, high_severity_issues: 2 })
    renderApp('/learning')

    expect(await screen.findByText('Based on all 2 saved reviews.')).toBeInTheDocument()
    expect(screen.getAllByText(/aren't necessarily the same mistake/).length).toBeGreaterThan(0)
    expect(screen.getByText(/a lower number isn't proof of improvement/)).toBeInTheDocument()
    expect(screen.queryByText(/\bXP\b/)).not.toBeInTheDocument()
    expect(screen.queryByText(/level \d/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument()
  })

  it('warns when not every saved review was loaded', async () => {
    api.getCodeReviews.mockResolvedValue(reviews)
    api.getReviewHistoryStats.mockResolvedValue({ total_reviews: 5, completed_reviews: 5, total_issues: 9, high_severity_issues: 2 })
    renderApp('/learning')

    expect(await screen.findByText(/Based on 2 of 5 saved reviews/)).toBeInTheDocument()
    expect(screen.getByText(/these numbers are incomplete/)).toBeInTheDocument()
  })

  it('lists repeated categories with links to each review', async () => {
    api.getCodeReviews.mockResolvedValue(reviews)
    renderApp('/learning')

    fireEvent.click(await screen.findByRole('tab', { name: 'Repeated categories' }))
    expect(screen.getByRole('tab', { name: 'Repeated categories' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('link', { name: '#5' })).toHaveAttribute('href', '/reviews/5')
    expect(screen.getByRole('link', { name: '#6' })).toHaveAttribute('href', '/reviews/6')
  })

  it('supports arrow-key tab navigation with every panel linked', async () => {
    api.getCodeReviews.mockResolvedValue(reviews)
    renderApp('/learning')

    const overview = await screen.findByRole('tab', { name: 'Overview' })
    for (const tab of screen.getAllByRole('tab')) {
      expect(document.getElementById(tab.getAttribute('aria-controls'))).not.toBeNull()
    }
    overview.focus()
    fireEvent.keyDown(overview, { key: 'ArrowRight' })
    const repeatedTab = screen.getByRole('tab', { name: 'Repeated categories' })
    expect(repeatedTab).toHaveAttribute('aria-selected', 'true')
    expect(repeatedTab).toHaveFocus()
    fireEvent.keyDown(repeatedTab, { key: 'End' })
    expect(screen.getByRole('tab', { name: 'Guidance' })).toHaveAttribute('aria-selected', 'true')
  })

  it('shows an error state with retry', async () => {
    api.getCodeReviews.mockRejectedValueOnce(new Error('offline'))
    renderApp('/learning')

    fireEvent.click(await screen.findByRole('button', { name: 'Try again' }))
    // Default stats report 12 saved reviews but only 1 was loaded.
    expect(await screen.findByText(/Based on 1 of 12 saved reviews/)).toBeInTheDocument()
  })
})

describe('Projects', () => {
  it('lists projects from the existing endpoint', async () => {
    renderApp('/projects')
    expect(await screen.findByRole('heading', { level: 2, name: 'Login App' })).toBeInTheDocument()
    expect(screen.getByText('User authentication')).toBeInTheDocument()
  })
})
