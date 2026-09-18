import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockFetchRoutes } from '../test/mockFetch'
import { api, ApiError, UnexpectedResponseError } from './client'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('api client', () => {
  it('returns the parsed body on success', async () => {
    mockFetchRoutes([{ match: (url) => url.endsWith('/accounts'), status: 200, body: [{ id: 'ACC-ACME', name: 'Acme' }] }])
    const accounts = await api.listAccounts()
    expect(accounts).toEqual([{ id: 'ACC-ACME', name: 'Acme' }])
  })

  it('throws ApiError with error_code/message on a contract-shaped error response', async () => {
    mockFetchRoutes([
      {
        match: (url) => url.endsWith('/auth/login'),
        status: 401,
        body: { error_code: 'INVALID_CREDENTIALS', message: 'Incorrect username or password.' },
      },
    ])
    await expect(api.login('demo', 'wrong')).rejects.toMatchObject({
      errorCode: 'INVALID_CREDENTIALS',
      status: 401,
    })
  })

  it('is an instance of ApiError, not a generic Error, for contract-shaped errors', async () => {
    mockFetchRoutes([
      { match: (url) => url.endsWith('/qa'), status: 400, body: { error_code: 'EMPTY_QUESTION', message: 'Cannot ask an empty question.' } },
    ])
    try {
      await api.ask('   ')
      expect.unreachable()
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
    }
  })

  it('throws UnexpectedResponseError when a non-2xx body is not the contract Error shape', async () => {
    mockFetchRoutes([{ match: (url) => url.endsWith('/qa'), status: 502, body: { not_the_contract: true } }])
    await expect(api.ask('hi')).rejects.toBeInstanceOf(UnexpectedResponseError)
  })

  it('sends credentials: include on every request (session cookie)', async () => {
    const { fetchMock } = mockFetchRoutes([{ match: (url) => url.endsWith('/accounts'), status: 200, body: [] }])
    await api.listAccounts()
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.credentials).toBe('include')
  })

  it('does not set Content-Type for a FormData (business-card) request', async () => {
    const { fetchMock } = mockFetchRoutes([{ match: (url) => url.endsWith('/interactions'), status: 201, body: {} }])
    const file = new File(['x'], 'card.png', { type: 'image/png' })
    await api.captureBusinessCard(file)
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect((init.headers as Record<string, string>)['Content-Type']).toBeUndefined()
  })
})
