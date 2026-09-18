/// <reference types="node" />
/**
 * Real integration evidence, per DEVELOPMENT-CONTRACT.md/frontend-agent.md's
 * "On integration evidence" section: exercises the selected journey against
 * the REAL backend (a genuinely running FastAPI process, real SQLite, real
 * Chroma), not a mock. Skipped automatically (not failed) when no backend is
 * reachable at INTEGRATION_BASE_URL, so this suite never silently substitutes
 * a mock for the real thing -- see the reachability check below.
 *
 * Run standalone: start the backend per its own report's "Local run"
 * instructions on port 8123 with a disposable DATABASE_PATH/CHROMA_PERSIST_DIR,
 * then `INTEGRATION_BASE_URL=http://127.0.0.1:8123 npx vitest run src/test/integration.test.ts`.
 */
import { describe, expect, it } from 'vitest'

const BASE_URL = process.env.INTEGRATION_BASE_URL ?? 'http://127.0.0.1:8123'
const USERNAME = process.env.INTEGRATION_USERNAME ?? 'demo'
const PASSWORD = process.env.INTEGRATION_PASSWORD ?? 'demo-password-for-integration-test'

/** Node's fetch does not persist cookies across calls the way a browser does -- this is a minimal manual jar. */
function makeCookieClient() {
  let cookie: string | null = null
  return async (path: string, init: RequestInit = {}) => {
    const response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        ...(init.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
        ...(cookie ? { Cookie: cookie } : {}),
        ...init.headers,
      },
    })
    const setCookie = response.headers.get('set-cookie')
    if (setCookie) cookie = setCookie.split(';')[0]
    return response
  }
}

// Top-level await: this file's module evaluation itself decides whether the
// backend is reachable, BEFORE any describe/it block is collected -- Vitest
// evaluates describe.skipIf's condition synchronously at collection time, so
// the check cannot live in a beforeAll (which runs too late to gate `skip`).
let backendReachable = false
try {
  const res = await fetch(`${BASE_URL}/health`)
  backendReachable = res.ok
} catch {
  backendReachable = false
}
if (!backendReachable) {
  console.warn(
    `Integration suite SKIPPED: no backend reachable at ${BASE_URL}/health. ` +
      'This is not evidence of integration -- start the real backend (see the backend report\'s "Local run" section) to actually exercise this suite.',
  )
}

describe.skipIf(!backendReachable)('real backend integration', () => {
  it('logs in, captures a typed interaction, and gets it back via GET /accounts + POST /qa', async () => {
    const client = makeCookieClient()

    const login = await client('/auth/login', { method: 'POST', body: JSON.stringify({ username: USERNAME, password: PASSWORD }) })
    expect(login.status).toBe(200)
    expect(await login.json()).toEqual({ authenticated: true })

    const accounts = await client('/accounts')
    expect(accounts.status).toBe(200)
    const accountList = (await accounts.json()) as { id: string; name: string }[]
    expect(accountList.some((a) => a.name === 'Acme')).toBe(true)

    const capture = await client('/interactions', {
      method: 'POST',
      body: JSON.stringify({ raw_text: 'met Priya from Acme, they want a demo by Friday -- integration test marker XYZQ' }),
    })
    expect(capture.status).toBe(201)
    const interaction = await capture.json()
    expect(interaction.match_status).toBe('matched')
    expect(interaction.account_id).toBe('ACC-ACME')
    expect(interaction.attendees.some((a: { name: string }) => a.name === 'Priya')).toBe(true)

    const ask = await client('/qa', { method: 'POST', body: JSON.stringify({ question: 'what did we discuss last time with Acme' }) })
    expect(ask.status).toBe(200)
    const qaBody = await ask.json()
    expect(qaBody.resolution).toBe('answered')
    expect(qaBody.answer_text).toContain('XYZQ')
  })

  it('surfaces the real 400 error shape (flat error_code/message) for an empty note', async () => {
    const client = makeCookieClient()
    await client('/auth/login', { method: 'POST', body: JSON.stringify({ username: USERNAME, password: PASSWORD }) })

    const response = await client('/interactions', { method: 'POST', body: JSON.stringify({ raw_text: '   ' }) })
    expect(response.status).toBe(400)
    const body = await response.json()
    expect(body.error_code).toBe('EMPTY_NOTE')
    expect(body.message).toBe('Cannot save an empty note.')
  })

  it('rejects protected access without a session with a real 401', async () => {
    const response = await fetch(`${BASE_URL}/accounts`)
    expect(response.status).toBe(401)
    const body = await response.json()
    expect(body.error_code).toBe('UNAUTHENTICATED')
  })
})
