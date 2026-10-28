import { fireEvent, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../services/api'
import { mockApi } from './fixtures'
import { renderApp } from './utils'

vi.mock('../services/api')

beforeEach(() => {
  vi.resetAllMocks()
  mockApi(api)
})

describe('Navigation', () => {
  it('moves between every page from the sidebar', async () => {
    renderApp('/')
    expect(await screen.findByRole('heading', { level: 1, name: /Let's ship cleaner code/ })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: 'New Review' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'New review' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: 'History' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Review history' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: 'Learning' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Your learning profile' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: 'Projects' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Projects' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: 'Home' }))
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/$/)
    await screen.findByText('10 of 12 completed')
  })

  it('marks the current section, treating review results as History', async () => {
    renderApp('/reviews/5')
    await screen.findByRole('heading', { level: 1, name: 'Login App' })
    expect(screen.getByRole('link', { name: 'History' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Home' })).not.toHaveAttribute('aria-current')
  })

  it('toggles the mobile menu', async () => {
    renderApp('/')
    const toggle = screen.getByRole('button', { name: 'Open menu' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(toggle)
    expect(screen.getByRole('button', { name: 'Close menu' })).toHaveAttribute('aria-expanded', 'true')
    await screen.findByText('API online')
  })

  it('reports when the API is unreachable', async () => {
    api.getHealth.mockRejectedValue(new Error('offline'))
    renderApp('/')
    expect(await screen.findByText('API unreachable')).toBeInTheDocument()
  })

  it('shows a not-found page for unknown routes', async () => {
    renderApp('/nope')
    expect(screen.getByText('Page not found')).toBeInTheDocument()
    await screen.findByText('API online')
  })
})
