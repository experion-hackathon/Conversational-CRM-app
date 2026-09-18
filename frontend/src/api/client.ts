import type {
  Account,
  BriefResponse,
  Commitment,
  DueCommitmentsResponse,
  ErrorResponse,
  Interaction,
  LoginResponse,
  LogoutResponse,
  QAResponse,
} from './types'

/** Overridable in tests; defaults to the Vite dev-server proxy path (see vite.config.ts). */
const BASE_URL = (import.meta as unknown as { env?: { VITE_API_BASE_URL?: string } }).env
  ?.VITE_API_BASE_URL ?? '/api'

/**
 * The HTTP implementation this module actually calls, as an explicit,
 * reassignable reference -- not a bare `fetch(...)` call against the shared
 * global. Monkey-patching `globalThis.fetch` directly (`vi.stubGlobal`/
 * `vi.spyOn(globalThis, 'fetch')`) raced unpredictably with Node's built-in
 * fetch global in this test environment: it reverted to the real
 * implementation partway through a single test for reasons that did not
 * reproduce deterministically even under direct property-descriptor
 * instrumentation. Dependency-injecting the implementation sidesteps that
 * whole class of global-mutation fragility rather than chasing its exact
 * cause further.
 */
let httpFetch: typeof fetch = (...args: Parameters<typeof fetch>) => fetch(...args)

/** Test-only hook -- see src/test/mockFetch.ts. */
export function __setHttpFetchForTests(impl: typeof fetch) {
  httpFetch = impl
}

export class ApiError extends Error {
  status: number
  errorCode: string
  details: Record<string, unknown> | null

  constructor(status: number, body: ErrorResponse) {
    super(body.message)
    this.name = 'ApiError'
    this.status = status
    this.errorCode = body.error_code
    this.details = body.details ?? null
  }
}

/** Thrown when a non-2xx response could not even be parsed as the contract's flat Error shape. */
export class UnexpectedResponseError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'UnexpectedResponseError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await httpFetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      ...(init?.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })

  if (response.status === 204) return undefined as T

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    if (!response.ok) throw new UnexpectedResponseError(response.status, 'The server returned a response that could not be parsed.')
    payload = undefined
  }

  if (!response.ok) {
    if (payload && typeof payload === 'object' && 'error_code' in payload && 'message' in payload) {
      throw new ApiError(response.status, payload as ErrorResponse)
    }
    throw new UnexpectedResponseError(response.status, 'The server returned an unexpected error response.')
  }

  return payload as T
}

export const api = {
  login: (username: string, password: string) =>
    request<LoginResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),

  logout: () => request<LogoutResponse>('/auth/logout', { method: 'POST' }),

  listAccounts: () => request<Account[]>('/accounts'),

  captureTyped: (rawText: string, accountId?: string) =>
    request<Interaction>('/interactions', {
      method: 'POST',
      body: JSON.stringify({ raw_text: rawText, ...(accountId ? { account_id: accountId } : {}) }),
    }),

  captureBusinessCard: (image: File) => {
    const form = new FormData()
    form.append('business_card_image', image)
    return request<Interaction>('/interactions', { method: 'POST', body: form })
  },

  listUnmatched: () => request<Interaction[]>('/interactions/unmatched'),

  resolveCustomer: (interactionId: string, accountId: string) =>
    request<Interaction>(`/interactions/${interactionId}/resolve-customer`, {
      method: 'POST',
      body: JSON.stringify({ account_id: accountId }),
    }),

  ask: (question: string, accountId?: string) =>
    request<QAResponse>('/qa', {
      method: 'POST',
      body: JSON.stringify({ question, ...(accountId ? { account_id: accountId } : {}) }),
    }),

  brief: (requestText: string, accountId?: string) =>
    request<BriefResponse>('/briefs', {
      method: 'POST',
      body: JSON.stringify({ request_text: requestText, ...(accountId ? { account_id: accountId } : {}) }),
    }),

  dueCommitments: (dueSoonWindowDays?: number) => {
    const query = dueSoonWindowDays ? `?due_soon_window_days=${dueSoonWindowDays}` : ''
    return request<DueCommitmentsResponse>(`/commitments/due${query}`)
  },

  completeCommitment: (commitmentId: string) =>
    request<Commitment>(`/commitments/${commitmentId}/complete`, { method: 'PATCH' }),
}
