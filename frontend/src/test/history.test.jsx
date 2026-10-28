import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { historyItem, mockApi, review } from './fixtures'
import { renderApp } from './utils'

vi.mock('../services/api')

const eightItems = () => Array.from({ length: 8 }, (_, index) => historyItem({ id: 20 - index }))

beforeEach(() => {
  vi.resetAllMocks()
  mockApi(api)
})

describe('Review History (Stage 6)', () => {
  it('renders lightweight summaries with the severity split and project names', async () => {
    api.getReviewHistory.mockResolvedValue({
      items: [
        historyItem(),
        historyItem({ id: 2, review_status: 'failed', issue_count: 0, high_severity_count: 0, medium_severity_count: 0, low_severity_count: 0 }),
      ],
      total: 2,
    })
    renderApp('/history')

    expect(await screen.findByText('4 (1H 2M 1L)')).toBeInTheDocument()
    expect(await screen.findAllByText('Login App')).toHaveLength(2)
    expect(screen.getByText('n/a')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry review 2' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open review 1' })).toBeInTheDocument()
  })

  it('offers only the stored language values and filters by cpp', async () => {
    renderApp('/history')
    const select = await screen.findByLabelText('Language')

    expect([...select.options].map((option) => option.value)).toEqual(
      ['', 'python', 'javascript', 'java', 'c', 'cpp', 'other'],
    )
    expect(screen.getByRole('option', { name: 'C++' })).toHaveValue('cpp')

    fireEvent.change(select, { target: { value: 'cpp' } })
    await waitFor(() => expect(api.getReviewHistory).toHaveBeenLastCalledWith(
      expect.objectContaining({ language: 'cpp', offset: 0 }),
    ))
    expect(screen.getByTestId('location')).toHaveTextContent('/history?language=cpp')
  })

  it('debounces the search by 300 ms and sends a single request', async () => {
    renderApp('/history')
    await screen.findByText('4 (1H 2M 1L)')
    const callsBefore = api.getReviewHistory.mock.calls.length

    vi.useFakeTimers()
    const input = screen.getByLabelText('Search code or language')
    fireEvent.change(input, { target: { value: 's' } })
    fireEvent.change(input, { target: { value: 'sam' } })
    fireEvent.change(input, { target: { value: 'sample' } })
    act(() => { vi.advanceTimersByTime(299) })
    expect(api.getReviewHistory.mock.calls.length).toBe(callsBefore)
    act(() => { vi.advanceTimersByTime(1) })
    vi.useRealTimers()

    await waitFor(() => expect(api.getReviewHistory).toHaveBeenLastCalledWith(
      expect.objectContaining({ q: 'sample', offset: 0 }),
    ))
    const searches = api.getReviewHistory.mock.calls.slice(callsBefore).map(([args]) => args.q).filter(Boolean)
    expect(searches).toEqual(['sample'])
  })

  it('filters by status, paginates, and scopes stats to the filters', async () => {
    api.getReviewHistory.mockResolvedValue({ items: eightItems(), total: 12 })
    renderApp('/history')

    await screen.findByText('Page 1 of 2')
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(api.getReviewHistory).toHaveBeenLastCalledWith(
      expect.objectContaining({ offset: 8 }),
    ))

    fireEvent.click(screen.getByRole('button', { name: 'Failed' }))
    await waitFor(() => expect(api.getReviewHistory).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'failed', offset: 0 }),
    ))
    expect(api.getReviewHistoryStats).toHaveBeenLastCalledWith({ q: '', language: '', status: 'failed' })
    expect(screen.getByText(/Totals for reviews matching the current filters/)).toBeInTheDocument()
  })

  it('keeps search, filters and page when returning from a review', async () => {
    api.getReviewHistory.mockResolvedValue({ items: eightItems(), total: 12 })
    api.getReviewHistoryDetail.mockResolvedValue(review({ id: 20 }))
    renderApp('/history?q=query&language=cpp&status=completed&page=2')

    await screen.findByText('Page 2 of 2')
    expect(screen.getByLabelText('Search code or language')).toHaveValue('query')

    fireEvent.click(screen.getByRole('button', { name: 'Open review 20' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Login App' })).toBeInTheDocument()
    expect(api.getReviewHistoryDetail).toHaveBeenCalledWith('20')

    fireEvent.click(screen.getByRole('link', { name: /Back to history/ }))
    await screen.findByText('Page 2 of 2')
    expect(screen.getByLabelText('Language')).toHaveValue('cpp')
    expect(screen.getByLabelText('Search code or language')).toHaveValue('query')
    expect(api.getReviewHistory).toHaveBeenLastCalledWith(
      { q: 'query', language: 'cpp', status: 'completed', limit: 8, offset: 8 },
    )
  })

  it('keeps a search typed just before opening a review', async () => {
    renderApp('/history')
    await screen.findByText('4 (1H 2M 1L)')

    fireEvent.change(screen.getByLabelText('Search code or language'), { target: { value: 'login' } })
    fireEvent.click(screen.getByRole('button', { name: 'Open review 1' }))
    fireEvent.click(await screen.findByRole('link', { name: /Back to history/ }))

    expect(await screen.findByLabelText('Search code or language')).toHaveValue('login')
    expect(screen.getByTestId('location')).toHaveTextContent('/history?q=login')
  })

  it('resets the search box when the URL changes from outside', async () => {
    renderApp('/history')
    await screen.findByText('4 (1H 2M 1L)')

    fireEvent.change(screen.getByLabelText('Search code or language'), { target: { value: 'foo' } })
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/history?q=foo'))

    fireEvent.click(screen.getByRole('link', { name: 'History' }))
    await waitFor(() => expect(screen.getByLabelText('Search code or language')).toHaveValue(''))
    // The old search must not be written back after the debounce delay.
    await new Promise((resolve) => setTimeout(resolve, 400))
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/history$/)
  })

  it('shows the error state and retries', async () => {
    api.getReviewHistory.mockRejectedValueOnce(new Error('offline'))
    renderApp('/history')

    expect(await screen.findByText('Could not load review history. Check the backend connection.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('4 (1H 2M 1L)')).toBeInTheDocument()
  })

  it('shows the empty state', async () => {
    api.getReviewHistory.mockResolvedValue({ items: [], total: 0 })
    renderApp('/history')
    expect(await screen.findByText('No reviews match these filters.')).toBeInTheDocument()
  })
})
