import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { mockFetchRoutes } from './test/mockFetch'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App routing / auth boundary', () => {
  it('redirects an unauthenticated visitor to /login', () => {
    mockFetchRoutes([])
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Conversational CRM' })).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
  })

  it('renders the protected home screen after a successful login', async () => {
    mockFetchRoutes([
      { match: (url) => url.endsWith('/auth/login'), status: 200, body: { authenticated: true } },
      { match: (url) => url.includes('/commitments/due'), status: 200, body: { overdue: [], due_soon: [], unspecified: [], message: 'There are no due-soon or overdue commitments right now.' } },
    ])
    render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>,
    )
    await userEvent.type(screen.getByLabelText('Username'), 'demo')
    await userEvent.type(screen.getByLabelText('Password'), 'demo-password')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Welcome back, demo' })).toBeInTheDocument()
    // Wait for the page's own async load to genuinely settle (not just its
    // static heading, which renders before the effect even runs) so no
    // pending effect from this test's component instance can leak into and
    // race with the next test after this one returns and its fetch mock is
    // torn down.
    expect(await screen.findByText('There are no due-soon or overdue commitments right now.')).toBeInTheDocument()
  })

  it('redirects back to /login when a protected-page API call comes back 401', async () => {
    mockFetchRoutes([
      { match: (url) => url.endsWith('/auth/login'), status: 200, body: { authenticated: true } },
      { match: (url) => url.includes('/commitments/due'), status: 401, body: { error_code: 'UNAUTHENTICATED', message: 'No valid session. Please log in.' } },
    ])
    render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>,
    )
    await userEvent.type(screen.getByLabelText('Username'), 'demo')
    await userEvent.type(screen.getByLabelText('Password'), 'demo-password')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    // The home screen's own load() call 401s (session expired server-side) --
    // useAuthAwareCall must flip auth state back and the ProtectedRoute
    // guard sends the user back to /login, even though this tab believed
    // it was logged in a moment ago.
    expect(await screen.findByLabelText('Username')).toBeInTheDocument()
  })
})
