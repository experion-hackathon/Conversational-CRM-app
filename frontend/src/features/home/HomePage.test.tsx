import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockFetchRoutes } from '../../test/mockFetch'
import { renderWithProviders } from '../../test/renderWithProviders'
import { HomePage } from './HomePage'

afterEach(() => {
  vi.restoreAllMocks()
})

const dueSoonCommitment = { id: 'CMT-1', account_id: 'ACC-ACME', interaction_id: 'INT-1', text: 'send pricing sheet', due_date: '2026-09-20', status: 'open' as const }
const accountsRoute = { match: (url: string) => url.endsWith('/accounts'), status: 200, body: [{ id: 'ACC-ACME', name: 'Acme' }] }

describe('HomePage', () => {
  it('shows the empty-state message when nothing is due', async () => {
    mockFetchRoutes([accountsRoute, { match: (url) => url.includes('/commitments/due'), status: 200, body: { overdue: [], due_soon: [], unspecified: [], message: 'There are no due-soon or overdue commitments right now.' } }])
    renderWithProviders(<HomePage />)
    expect(await screen.findByText('There are no due-soon or overdue commitments right now.')).toBeInTheDocument()
  })

  it('lists to-do items from overdue + due_soon', async () => {
    mockFetchRoutes([accountsRoute, { match: (url) => url.includes('/commitments/due'), status: 200, body: { overdue: [], due_soon: [dueSoonCommitment], unspecified: [], message: null } }])
    renderWithProviders(<HomePage />)
    expect(await screen.findByText(/send pricing sheet/)).toBeInTheDocument()
  })

  it('routes a question-shaped entry to /qa, not /interactions', async () => {
    const { fetchMock } = mockFetchRoutes([
      accountsRoute,
      { match: (url) => url.includes('/commitments/due'), status: 200, body: { overdue: [], due_soon: [], unspecified: [], message: 'There are no due-soon or overdue commitments right now.' } },
      { match: (url) => url.endsWith('/qa'), status: 200, body: { resolution: 'answered', account_id: 'ACC-ACME', answer_text: 'discussed pricing', message: null } },
    ])
    renderWithProviders(<HomePage />)
    await screen.findByText('There are no due-soon or overdue commitments right now.')

    const composer = screen.getByLabelText('Capture a note or ask a question')
    await userEvent.type(composer, 'What did we discuss last time with Acme?')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('discussed pricing')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/qa'))).toBe(true)
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/interactions'))).toBe(false)
    // Unlike a capture, asking a question changes nothing about the to-do
    // list, so it deliberately does not reload /commitments/due -- only the
    // initial page-load call should ever have happened.
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/commitments/due')).length).toBe(1)
  })

  it('routes a non-question entry to /interactions (capture), not /qa', async () => {
    const { fetchMock } = mockFetchRoutes([
      accountsRoute,
      { match: (url) => url.includes('/commitments/due'), status: 200, body: { overdue: [], due_soon: [], unspecified: [], message: 'There are no due-soon or overdue commitments right now.' } },
      {
        match: (url) => url.endsWith('/interactions'),
        status: 201,
        body: { id: 'INT-1', account_id: 'ACC-ACME', raw_text: 'met with Acme', source_type: 'typed', match_status: 'matched', manual_entry_required: false, captured_at: '2026-09-18T00:00:00Z', attendees: [], commitments: [] },
      },
    ])
    renderWithProviders(<HomePage />)
    await screen.findByText('There are no due-soon or overdue commitments right now.')

    const composer = screen.getByLabelText('Capture a note or ask a question')
    await userEvent.type(composer, 'met with Acme, discussed renewal')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('Saved and matched to a customer.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/interactions'))).toBe(true)
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/qa'))).toBe(false)
    // Same settlement wait as the sibling test above -- avoid leaking a
    // pending reload effect into the next test.
    await waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/commitments/due')).length).toBe(2))
  })
})
