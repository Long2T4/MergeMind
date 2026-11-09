import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { diffContext, parsePullRequestUrl, pullRequestProgress } from '../lib/pullRequest'
import * as api from '../services/api'
import { historyItem, mockApi, prFile, prReview, pullRequest } from './fixtures'
import { renderApp } from './utils'

vi.mock('../services/api')

const URL = 'https://github.com/octo-org/sample-repo/pull/7'

beforeEach(() => {
  vi.resetAllMocks()
  mockApi(api)
})

afterEach(() => {
  vi.useRealTimers()
})

describe('pull request helpers', () => {
  it('accepts only https://github.com/{owner}/{repo}/pull/{number}, like the backend', () => {
    expect(parsePullRequestUrl(` ${URL}/ `)).toEqual({ owner: 'octo-org', repo: 'sample-repo', number: 7 })
    for (const bad of [
      'http://github.com/octo-org/sample-repo/pull/7',
      'https://www.github.com/octo-org/sample-repo/pull/7',
      'https://github.com/octo-org/sample-repo/issues/7',
      `${URL}?x=1`, `${URL}#files`, `${URL}/files`,
      'https://github.com/octo-org/../pull/7',
      'https://github.com/octo-org/sample-repo/pull/0',
      'javascript:alert(1)', '',
    ]) {
      expect(parsePullRequestUrl(bad)).toBeNull()
    }
  })

  it('finds the flagged lines inside a file diff', () => {
    const patch = '@@ -3,1 +3,3 @@\n keep()\n-old()\n+one()\n+two()'
    expect(diffContext(patch, 4)).toEqual({ startLine: 3, code: 'keep()\none()\ntwo()', line: 4 })
    expect(diffContext(patch, 9)).toBeNull()
    expect(diffContext(null, 4)).toBeNull()
  })

  it('counts progress over the files that are being reviewed', () => {
    const pr = pullRequest({ files: [
      prFile({ review_state: 'reviewed' }), prFile({ review_state: 'failed' }),
      prFile({ review_state: 'pending' }), prFile({ review_state: 'skipped', skip_reason: 'generated' }),
    ] })
    expect(pullRequestProgress(pr)).toEqual({ done: 2, total: 3 })
  })
})

describe('New review: GitHub pull request', () => {
  async function openTab() {
    renderApp('/reviews/new')
    fireEvent.click(await screen.findByRole('button', { name: 'GitHub pull request' }))
    return screen.getByLabelText('Pull request URL')
  }

  it('validates the URL before calling the API, then starts the review', async () => {
    const input = await openTab()
    const submit = screen.getByRole('button', { name: /Review pull request/ })

    fireEvent.change(input, { target: { value: 'https://github.com/octo-org/sample-repo/issues/7' } })
    fireEvent.click(submit)
    expect(await screen.findByText(/pull request URL like/)).toBeInTheDocument()
    expect(api.createPullRequestReview).not.toHaveBeenCalled()

    fireEvent.change(input, { target: { value: URL } })
    fireEvent.click(submit)
    await waitFor(() => expect(api.createPullRequestReview).toHaveBeenCalledWith({
      projectId: 1, prUrl: URL, sourceRoot: '',
    }))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/reviews/42'))
  })

  it('shows the server explanation for private, oversized or rate-limited pull requests', async () => {
    api.createPullRequestReview.mockRejectedValue(Object.assign(
      new Error("GitHub's rate limit was reached. Try again in 60 seconds."), { validation: true }))
    const input = await openTab()
    fireEvent.change(input, { target: { value: URL } })
    fireEvent.click(screen.getByRole('button', { name: /Review pull request/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('rate limit was reached')
  })

  it('keeps the paste-code form as the default', async () => {
    renderApp('/reviews/new')
    expect(await screen.findByRole('button', { name: 'Paste code' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByLabelText('Paste your code')).toBeInTheDocument()
  })
})

describe('Pull request review results', () => {
  it('shows the pull request, changed files, per-file findings and outside-the-diff labels', async () => {
    api.getReviewHistoryDetail.mockResolvedValue(prReview())
    renderApp('/reviews/9')

    const link = await screen.findByRole('link', { name: /octo-org\/sample-repo#7/ })
    expect(link).toHaveAttribute('href', 'https://github.com/octo-org/sample-repo/pull/7')
    expect(screen.getByText('Add user creation')).toBeInTheDocument()
    expect(screen.getByText('octo-student')).toBeInTheDocument()
    expect(screen.getByText('aaaaaaa')).toBeInTheDocument()

    const files = screen.getByRole('region', { name: 'Changed files' })
    expect(within(files).getByText('package-lock.json')).toBeInTheDocument()
    expect(within(files).getByText('Skipped: generated file')).toBeInTheDocument()
    expect(within(files).getAllByText('Reviewed')).toHaveLength(2)

    expect(screen.getAllByText('Outside the diff')).toHaveLength(1)
    expect(screen.getAllByText('src/app.py', { selector: '.issue-card-file' })).toHaveLength(2)

    fireEvent.click(screen.getByRole('button', { name: 'src/util.py · 1' }))
    expect(screen.getByText('add subtracts')).toBeInTheDocument()
    expect(screen.queryByText('eval is dangerous')).not.toBeInTheDocument()
  })

  it('checks for progress while a pull request review is pending, then stops', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const pending = prReview({
      review_status: 'pending', risk_score: null, risk_level: null, risk_breakdown: null, issues: [],
      pull_request: pullRequest({ files: [prFile(), prFile({ id: 2, path: 'src/util.py', review_state: 'pending' })] }),
    })
    api.getReviewHistoryDetail.mockResolvedValueOnce(pending).mockResolvedValue(prReview())
    renderApp('/reviews/9')

    expect(await screen.findByText('Reviewing files: 1 of 2 done')).toBeInTheDocument()
    await act(() => vi.advanceTimersByTimeAsync(3000))
    expect(await screen.findByText('Empty names reach User')).toBeInTheDocument()
    expect(screen.queryByText(/Reviewing files/)).not.toBeInTheDocument()

    await act(() => vi.advanceTimersByTimeAsync(15000))
    expect(api.getReviewHistoryDetail).toHaveBeenCalledTimes(2)
  })

  it('stops checking when the page is left', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    api.getReviewHistoryDetail.mockResolvedValue(prReview({ review_status: 'pending', issues: [] }))
    const { unmount } = renderApp('/reviews/9')
    await screen.findByText(/Reviewing files/)
    unmount()
    await act(() => vi.advanceTimersByTimeAsync(15000))
    expect(api.getReviewHistoryDetail).toHaveBeenCalledTimes(1)
  })

  it('explains when it stops checking a review that never finishes', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    api.getReviewHistoryDetail.mockResolvedValue(prReview({ review_status: 'pending', issues: [] }))
    renderApp('/reviews/9')
    await screen.findByText(/Reviewing files/)
    for (let poll = 0; poll < 200; poll += 1) {
      await act(() => vi.advanceTimersByTimeAsync(3000))
    }
    expect(await screen.findByText(/taking longer than expected/)).toBeInTheDocument()
    const calls = api.getReviewHistoryDetail.mock.calls.length
    await act(() => vi.advanceTimersByTimeAsync(30000))
    expect(api.getReviewHistoryDetail).toHaveBeenCalledTimes(calls)
  })

  it('does not poll stuck manual reviews', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    api.getReviewHistoryDetail.mockResolvedValue(prReview({ review_status: 'pending', pull_request: null, pull_request_id: null }))
    renderApp('/reviews/9')
    await screen.findByText('This review is still in progress.')
    await act(() => vi.advanceTimersByTimeAsync(15000))
    expect(api.getReviewHistoryDetail).toHaveBeenCalledTimes(1)
  })
})

describe('History with pull request reviews', () => {
  it('labels pull request rows and leaves manual rows unchanged', async () => {
    api.getReviewHistory.mockResolvedValue({ items: [
      historyItem({ id: 9, pull_request_id: 3, pr_repo: 'octo-org/sample-repo', pr_number: 7, pr_title: 'Add user creation' }),
      historyItem({ id: 1 }),
    ], total: 2, limit: 8, offset: 0 })
    renderApp('/history')

    expect(await screen.findByText(/Review #9 · octo-org\/sample-repo#7 · Add user creation/)).toBeInTheDocument()
    expect(screen.getByText(/Review #1 · print\('hello'\)/)).toBeInTheDocument()
  })
})
