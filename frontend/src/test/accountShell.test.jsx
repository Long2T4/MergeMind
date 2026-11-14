import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { ROUTER_FUTURE } from '../routerFuture'
import * as api from '../services/api'
import Stage12Shell from '../stage12/Stage12Shell'
import { mockApi } from './fixtures'

// A signed-in Supabase client, and the account check the shell runs once.
const fake = vi.hoisted(() => ({ me: null, signOut: null }))

vi.mock('../services/api')
vi.mock('../stage12/auth', () => ({
  API_BASE: 'http://localhost:8000',
  authFetch: (url, options) => fetch(url, options),
  accountRequest: (path) => (path === '/me' ? fake.me() : Promise.resolve([])),
  supabase: {
    auth: {
      getSession: async () => ({ data: { session: { user: { id: 'user-1', email: 'alice@example.com' } } }, error: null }),
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }),
      signOut: (...args) => fake.signOut(...args),
    },
  },
}))

function renderShell(route = '/') {
  return render(
    <MemoryRouter initialEntries={[route]} future={ROUTER_FUTURE}>
      <Stage12Shell><App /></Stage12Shell>
    </MemoryRouter>,
  )
}

function accountError(status, message) {
  return Object.assign(new Error(message), { status })
}

beforeEach(() => {
  vi.resetAllMocks()
  mockApi(api)
  fake.me = async () => ({ id: 1, email: 'alice@example.com' })
  fake.signOut = vi.fn(async () => ({ error: null }))
})

describe('Signed-in account in the sidebar', () => {
  it('shows the email and Log out in the sidebar, with no floating panel', async () => {
    renderShell('/reviews/new')

    const sidebar = await screen.findByRole('banner')
    expect(within(sidebar).getByText('alice@example.com')).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /Run review/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Account and learning/i })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Stage 12 dashboard')).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Log out' })).toHaveLength(1)

    fireEvent.click(within(sidebar).getByRole('button', { name: 'Log out' }))
    await waitFor(() => expect(fake.signOut).toHaveBeenCalledTimes(1))
  })

  it('keeps the account box inside the mobile menu', async () => {
    renderShell('/')
    const sidebar = await screen.findByRole('banner')
    const menu = sidebar.querySelector('#primary-navigation')
    expect(within(menu).getByText('alice@example.com')).toBeInTheDocument()
    expect(within(menu).getByRole('button', { name: 'Log out' })).toBeInTheDocument()
  })
})

describe('Accounts that need administrator linking', () => {
  it('explains the linking step instead of showing backend errors', async () => {
    fake.me = async () => { throw accountError(409, 'Existing account requires administrator linking') }
    renderShell('/history')

    expect(await screen.findByRole('heading', { name: 'This account needs to be linked' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/An administrator must link them/)
    expect(screen.getByText('alice@example.com')).toBeInTheDocument()
    expect(screen.queryByText(/Check the backend connection/)).not.toBeInTheDocument()
    expect(api.getReviewHistory).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Log out' }))
    await waitFor(() => expect(fake.signOut).toHaveBeenCalledTimes(1))
  })

  it("shows the server's reason when the sign-in has no verified email", async () => {
    fake.me = async () => { throw accountError(403, 'A verified email is required') }
    renderShell('/')
    expect(await screen.findByRole('heading', { name: 'This account can’t be opened' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('A verified email is required')
  })

  it('still opens the app when the account check fails for another reason', async () => {
    fake.me = async () => { throw accountError(undefined, 'Failed to fetch') }
    renderShell('/')
    expect(await screen.findByRole('banner')).toBeInTheDocument()
    expect(screen.queryByText('This account needs to be linked')).not.toBeInTheDocument()
  })
})
