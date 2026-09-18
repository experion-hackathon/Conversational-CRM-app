import { render, screen, waitFor } from '@testing-library/react'
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
    const { fetchMock } = mockFetchRoutes([
      { match: (url) => url.endsWith('/auth/login'), status: 200, body: { authenticated: true } },
      { match: (url) => url.endsWith('/accounts'), status: 200, body: [{ id: 'ACC-ACME', name: 'Acme' }] },
      { match: (url) => url.includes('/commitments/due'), status: 200, body: { overdue: [], due_soon: [], unspecified: [], message: 'There are no due-soon or overdue commitments right now.' } },
    ])
    const { unmount } = render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>,
    )
    await userEvent.type(screen.getByLabelText('Username'), 'demo')
    await userEvent.type(screen.getByLabelText('Password'), 'demo-password')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Welcome, John Doe' })).toBeInTheDocument()
    // Wait for the page's own async loads to genuinely settle (not just its
    // static heading, which renders before either effect even runs) so no
    // pending effect from this test's component instance -- including the
    // separate useAccounts() fetch the two-pane redesign added -- can leak
    // into and race with the next test after this one returns and its fetch
    // mock is torn down.
    expect(await screen.findByText('There are no due-soon or overdue commitments right now.')).toBeInTheDocument()
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/accounts'))).toBe(true))
    // Explicit unmount, not just implicit cleanup timing: a still-mounted
    // tree whose effects fire between here and the next test's render() is
    // exactly the leak class this whole settling dance exists to prevent.
    unmount()
  })

  it('redirects back to /login when a protected-page API call comes back 401', async () => {
    mockFetchRoutes([
      { match: (url) => url.endsWith('/auth/login'), status: 200, body: { authenticated: true } },
      { match: (url) => url.endsWith('/accounts'), status: 200, body: [{ id: 'ACC-ACME', name: 'Acme' }] },
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

    // Wait for the Home screen to actually appear first. Without this,
    // findByLabelText('Username') below can resolve against the *original*
    // pre-login LoginPage instance instead (login's own fetch hasn't
    // resolved yet at the exact instant it's called), which then goes stale
    // mid-assertion once login actually completes and replaces the tree -- a
    // real, confirmed race, not a timing/timeout issue. Anchoring on Home
    // first guarantees any Username field found afterward is the one from
    // the post-401-redirect instance, not the original pre-login one.
    await screen.findByRole('heading', { name: 'Welcome, John Doe' })

    // The home screen's own load() call 401s (session expired server-side) --
    // useAuthAwareCall must flip auth state back and the ProtectedRoute
    // guard sends the user back to /login, even though this tab believed
    // it was logged in a moment ago.
    expect(await screen.findByLabelText('Username')).toBeInTheDocument()
  })
})
