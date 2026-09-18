import { vi } from 'vitest'
import { __setHttpFetchForTests } from '../api/client'

interface MockRoute {
  match: (url: string, init?: RequestInit) => boolean
  status: number
  body: unknown
}

/**
 * A small, labeled fetch mock -- every route is explicit about the request it
 * matches and the exact response it returns. Used for unit/component tests
 * that must not depend on a real server; the integration test suite (see
 * src/test/integration.test.ts) is what actually exercises the real backend.
 */
export function mockFetchRoutes(routes: MockRoute[]) {
  const calls: { url: string; init?: RequestInit }[] = []
  const impl = async (input: string | URL | Request, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString()
    calls.push({ url, init })
    const route = routes.find((r) => r.match(url, init))
    if (!route) throw new Error(`mockFetchRoutes: no route matched ${init?.method ?? 'GET'} ${url}`)
    return new Response(JSON.stringify(route.body), {
      status: route.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }
  // Neither vi.stubGlobal nor vi.spyOn(globalThis, 'fetch') proved reliable
  // in this environment -- both raced with something that reverted
  // globalThis.fetch back to Node's real implementation partway through a
  // single test, confirmed via direct instrumentation (fetch.toString()
  // literally switched from the mock to Node's native fetch source mid-test).
  // Injecting the implementation directly into the API client sidesteps the
  // shared global entirely.
  const fetchMock = vi.fn(impl)
  __setHttpFetchForTests(fetchMock)
  return { fetchMock, calls }
}
