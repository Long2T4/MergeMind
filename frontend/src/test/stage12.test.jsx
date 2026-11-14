import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import * as auth from '../stage12/auth'
import { PROJECTS, issue, mockApi, review } from './fixtures'
import { renderApp } from './utils'

vi.mock('../services/api')

const LEARNING = {
  total_reviews: 2, total_issues: 3, fixed_issues: 1, false_positives: 1, pull_request_reviews: 0,
  statuses: { open: 1, fixed: 1, dismissed: 0, false_positive: 1 },
  categories: { Security: 2, Logic: 1 },
  category_outcomes: {
    Security: { open: 1, fixed: 0, dismissed: 0, false_positive: 1 },
    Logic: { open: 0, fixed: 1, dismissed: 0, false_positive: 0 },
  },
  repeated_categories: [], monthly_categories: [], trend_note: '',
}

beforeEach(() => {
  vi.resetAllMocks()
  mockApi(api)
})

afterEach(() => vi.restoreAllMocks())

describe('Finding feedback on Review Results', () => {
  it('shows an outcome control on each finding card, with Fixed labeled self-reported', async () => {
    api.getReviewHistoryDetail.mockResolvedValue(review({
      issues: [issue(), issue({ id: 12, title: 'Unvalidated input', status: 'dismissed' })],
    }))
    renderApp('/reviews/5')

    const controls = await screen.findAllByLabelText('Your outcome')
    expect(controls).toHaveLength(2)
    expect(controls.map((control) => control.value)).toEqual(['open', 'dismissed'])
    expect(within(controls[0]).getByRole('option', { name: 'Fixed (self-reported)' })).toBeInTheDocument()
    // The separate feedback list is gone; the controls live on the cards.
    expect(screen.queryByText('Developer feedback')).not.toBeInTheDocument()
    // ...so the old "not available yet" footnote is gone too.
    expect(screen.queryByText(/isn't available yet/)).not.toBeInTheDocument()
  })

  it('saves a new outcome and shows when it changed', async () => {
    const spy = vi.spyOn(auth, 'accountRequest').mockImplementation(async (path, options) => (
      path === '/findings/11'
        ? { id: 11, status: JSON.parse(options.body).status, status_updated_at: '2026-11-13T10:00:00', status_updated_by: 1 }
        : []))
    renderApp('/reviews/5')

    const control = await screen.findByLabelText('Your outcome')
    fireEvent.change(control, { target: { value: 'fixed' } })

    expect(await screen.findByText('Saved')).toBeInTheDocument()
    expect(control.value).toBe('fixed')
    expect(spy).toHaveBeenCalledWith('/findings/11', expect.objectContaining({
      method: 'PATCH', body: JSON.stringify({ status: 'fixed' }),
    }))
    expect(screen.getByText(/Last changed/)).toBeInTheDocument()
  })

  it('keeps the previous outcome and explains when saving fails', async () => {
    vi.spyOn(auth, 'accountRequest').mockImplementation(async (path) => {
      if (path === '/findings/11') throw new Error('Finding not found')
      return []
    })
    renderApp('/reviews/5')

    const control = await screen.findByLabelText('Your outcome')
    fireEvent.change(control, { target: { value: 'false_positive' } })

    expect(await screen.findByRole('alert')).toHaveTextContent('Finding not found')
    expect(control.value).toBe('open')
  })
})

describe('Learning outcomes by category', () => {
  it('shows each category with its outcomes, Fixed labeled self-reported', async () => {
    vi.spyOn(auth, 'accountRequest').mockImplementation(async (path) => (path === '/learning' ? LEARNING : []))
    renderApp('/learning')

    const table = await screen.findByRole('table', { name: 'Finding outcomes by category' })
    expect(within(table).getByRole('columnheader', { name: 'Fixed (self-reported)' })).toBeInTheDocument()
    const security = within(table).getByRole('row', { name: /Security/ })
    expect(within(security).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['1', '0', '0', '1'])
    const logic = within(table).getByRole('row', { name: /Logic/ })
    expect(within(logic).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['0', '1', '0', '0'])
  })

  it('is one learning page, without duplicate totals or placeholder text', async () => {
    vi.spyOn(auth, 'accountRequest').mockImplementation(async (path) => (path === '/learning' ? LEARNING : []))
    renderApp('/learning')

    const table = await screen.findByRole('table', { name: 'Finding outcomes by category' })
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
    expect(screen.getByRole('heading', { level: 2, name: 'Finding outcomes' })).toBeInTheDocument()
    expect(screen.queryByText('My learning progress')).not.toBeInTheDocument()
    expect(screen.getAllByText('Reviews')).toHaveLength(1)
    expect(screen.queryByText(/planned for Stage 12/)).not.toBeInTheDocument()
    const totals = within(table).getByRole('row', { name: /All categories/ })
    expect(within(totals).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['1', '1', '0', '1'])
  })
})

describe('Project renaming', () => {
  it('renames a project in place', async () => {
    const spy = vi.spyOn(auth, 'accountRequest').mockImplementation(async (path, options) => {
      if (path === '/projects' && !options) return PROJECTS
      if (path === '/projects/1') return { ...PROJECTS[0], name: JSON.parse(options.body).name }
      return []
    })
    renderApp('/projects')

    fireEvent.click(await screen.findByRole('button', { name: 'Rename Login App' }))
    const input = screen.getByLabelText('New name for Login App')
    fireEvent.change(input, { target: { value: 'Auth Service' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save name' }))

    expect(await screen.findByText('Auth Service')).toBeInTheDocument()
    expect(spy).toHaveBeenCalledWith('/projects/1', expect.objectContaining({
      method: 'PATCH', body: JSON.stringify({ name: 'Auth Service' }),
    }))
    expect(screen.queryByText('Login App')).not.toBeInTheDocument()
  })

  it('keeps the name and explains when renaming fails', async () => {
    vi.spyOn(auth, 'accountRequest').mockImplementation(async (path, options) => {
      if (path === '/projects' && !options) return PROJECTS
      throw new Error('Project name cannot be blank')
    })
    renderApp('/projects')

    fireEvent.click(await screen.findByRole('button', { name: 'Rename Login App' }))
    fireEvent.change(screen.getByLabelText('New name for Login App'), { target: { value: 'New' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save name' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Project name cannot be blank')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByText('Login App')).toBeInTheDocument()
  })
})

describe('Health check', () => {
  it('does not require signing in', async () => {
    const { getHealth } = await vi.importActual('../services/api')
    const authFetch = vi.spyOn(auth, 'authFetch')
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'ok' }) })
    vi.stubGlobal('fetch', fetch)

    await expect(getHealth()).resolves.toEqual({ status: 'ok' })
    expect(authFetch).not.toHaveBeenCalled()
    expect(fetch.mock.calls[0][1]?.headers?.Authorization).toBeUndefined()
    vi.unstubAllGlobals()
  })
})

describe('New Review projects', () => {
  const TWO_PROJECTS = [...PROJECTS, { ...PROJECTS[0], id: 2, name: 'Payments API' }]

  beforeEach(() => localStorage.clear())
  afterEach(() => localStorage.clear())

  it('asks a user with no projects to create one, instead of using another account project', async () => {
    api.getProjects.mockResolvedValue([])
    renderApp('/reviews/new')

    expect(await screen.findByText('Create a project first')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Go to Projects' })).toHaveAttribute('href', '/projects')
    expect(screen.queryByRole('button', { name: /Run review/ })).not.toBeInTheDocument()
    expect(screen.queryByText('Default project')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'GitHub pull request' }))
    expect(screen.getByText('Create a project first')).toBeInTheDocument()
    expect(screen.queryByLabelText('Pull request URL')).not.toBeInTheDocument()
    expect(api.createCodeReview).not.toHaveBeenCalled()
  })

  it('explains when the project list cannot be loaded', async () => {
    api.getProjects.mockRejectedValue(new Error('offline'))
    renderApp('/reviews/new')
    expect(await screen.findByText(/Could not load your projects/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Run review/ })).not.toBeInTheDocument()
  })

  it('uses the project selected on the Projects page', async () => {
    api.getProjects.mockResolvedValue(TWO_PROJECTS)
    vi.spyOn(auth, 'accountRequest').mockImplementation(async (path) => (path === '/projects' ? TWO_PROJECTS : []))
    renderApp('/projects')

    fireEvent.click(await screen.findByRole('button', { name: /^Payments API/ }))
    expect(screen.getByText('New reviews will use Payments API')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: 'New Review' }))
    expect(await screen.findByLabelText('Project')).toHaveValue('2')
    fireEvent.change(screen.getByLabelText('Paste your code'), { target: { value: 'print(1)' } })
    fireEvent.click(screen.getByRole('button', { name: /Run review/ }))
    await waitFor(() => expect(api.createCodeReview).toHaveBeenCalledWith(expect.objectContaining({ projectId: 2 })))
  })

  it('uses the selected project for pull request reviews too', async () => {
    api.getProjects.mockResolvedValue(TWO_PROJECTS)
    localStorage.setItem('mergemind_active_project', '2')
    renderApp('/reviews/new')

    fireEvent.click(await screen.findByRole('button', { name: 'GitHub pull request' }))
    expect(screen.getByLabelText('Project')).toHaveValue('2')
  })

  it('falls back to the first project when the saved selection is not one of yours', async () => {
    localStorage.setItem('mergemind_active_project', '99')
    renderApp('/reviews/new')
    expect(await screen.findByLabelText('Project')).toHaveValue('1')
  })
})
