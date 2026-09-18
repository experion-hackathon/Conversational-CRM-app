import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockFetchRoutes } from '../test/mockFetch'
import { renderWithProviders } from '../test/renderWithProviders'
import { LoginPage } from './LoginPage'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('LoginPage', () => {
  it('shows an inline error and does not navigate on invalid credentials', async () => {
    mockFetchRoutes([
      {
        match: (url) => url.endsWith('/auth/login'),
        status: 401,
        body: { error_code: 'INVALID_CREDENTIALS', message: 'Incorrect username or password.' },
      },
    ])
    renderWithProviders(<LoginPage />, { route: '/login' })

    await userEvent.type(screen.getByLabelText('Username'), 'demo')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect username or password.')
  })

  it('surfaces the lockout message distinctly on LOGIN_LOCKED', async () => {
    mockFetchRoutes([
      {
        match: (url) => url.endsWith('/auth/login'),
        status: 429,
        body: { error_code: 'LOGIN_LOCKED', message: 'Too many failed attempts. Try again later.' },
      },
    ])
    renderWithProviders(<LoginPage />, { route: '/login' })

    await userEvent.type(screen.getByLabelText('Username'), 'demo')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/Retry-After applies/)
  })

  it('calls login and disables the submit button while in flight', async () => {
    const { fetchMock } = mockFetchRoutes([{ match: (url) => url.endsWith('/auth/login'), status: 200, body: { authenticated: true } }])
    renderWithProviders(<LoginPage />, { route: '/login' })

    await userEvent.type(screen.getByLabelText('Username'), 'demo')
    await userEvent.type(screen.getByLabelText('Password'), 'demo-password')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({ username: 'demo', password: 'demo-password' })
  })
})
