import { fireEvent, screen, within } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { accountRequest } from '../stage12/auth'
import { issue, mockApi, prReview, review } from './fixtures'
import { renderApp } from './utils'

vi.mock('../services/api')
vi.mock('../stage12/auth', () => ({
  supabase: null,
  API_BASE: 'http://localhost:8000',
  accountRequest: vi.fn(),
}))

const explanation = {
  what_is_wrong: 'The function subtracts instead of adding.',
  why_it_matters: 'That gives you the wrong total.',
  before: 'return a - b',
  after: 'return a + b',
}
const buttonName = 'Explain like I’m new'

beforeEach(() => {
  vi.resetAllMocks()
  mockApi(api)
})

it.each([['manual', review], ['GitHub PR', prReview]])(
  'generates a beginner explanation for a %s finding and shows loading',
  async (_, makeReview) => {
    const data = makeReview()
    api.getReviewHistoryDetail.mockResolvedValue(data)
    let resolveRequest
    accountRequest.mockImplementation(() => new Promise((resolve) => { resolveRequest = resolve }))
    renderApp(`/reviews/${data.id}`)
    const button = await screen.findByRole('button', { name: buttonName })
    expect(accountRequest).not.toHaveBeenCalled()
    fireEvent.click(button)
    expect(button).toBeDisabled()
    expect(screen.getByText('Generating explanation…')).toBeInTheDocument()
    expect(accountRequest).toHaveBeenCalledWith(
      `/findings/${data.issues[0].id}/beginner-explanation`, { method: 'POST' },
    )

    resolveRequest(explanation)
    const panel = await screen.findByRole('region', { name: 'Beginner explanation' })
    expect(within(panel).getByText(explanation.what_is_wrong)).toBeInTheDocument()
    expect(within(panel).getByText(explanation.why_it_matters)).toBeInTheDocument()
    expect(panel).toHaveTextContent(explanation.before)
    expect(panel).toHaveTextContent(explanation.after)
    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(screen.queryByText('Generating explanation…')).not.toBeInTheDocument()
  },
)

it('opens a saved explanation without requesting another one', async () => {
  api.getReviewHistoryDetail.mockResolvedValue(review({ issues: [issue({ beginner_explanation: explanation })] }))
  renderApp('/reviews/5')
  const button = await screen.findByRole('button', { name: buttonName })
  fireEvent.click(button)
  expect(screen.getByText(explanation.what_is_wrong)).toBeVisible()
  fireEvent.click(button)
  expect(screen.queryByText(explanation.what_is_wrong)).not.toBeInTheDocument()
  expect(accountRequest).not.toHaveBeenCalled()
})

it('shows a failure and lets the user retry', async () => {
  api.getReviewHistoryDetail.mockResolvedValue(review())
  accountRequest.mockRejectedValueOnce(new Error('Could not generate the explanation. Try again.'))
  accountRequest.mockResolvedValueOnce(explanation)
  renderApp('/reviews/5')
  fireEvent.click(await screen.findByRole('button', { name: buttonName }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not generate the explanation')
  fireEvent.click(screen.getByRole('button', { name: 'Retry explanation' }))
  expect(await screen.findByText(explanation.what_is_wrong)).toBeVisible()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(accountRequest).toHaveBeenCalledTimes(2)
})
