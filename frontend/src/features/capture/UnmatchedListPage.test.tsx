import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockFetchRoutes } from '../../test/mockFetch'
import { renderWithProviders } from '../../test/renderWithProviders'
import { UnmatchedListPage } from './UnmatchedListPage'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('UnmatchedListPage', () => {
  it('shows an empty state when nothing is unmatched', async () => {
    mockFetchRoutes([
      { match: (url) => url.endsWith('/interactions/unmatched'), status: 200, body: [] },
      { match: (url) => url.endsWith('/accounts'), status: 200, body: [] },
    ])
    renderWithProviders(<UnmatchedListPage />)
    expect(await screen.findByText('Nothing needs customer selection right now.')).toBeInTheDocument()
  })

  it('lists unmatched notes and removes one after it is resolved', async () => {
    mockFetchRoutes([
      {
        match: (url) => url.endsWith('/interactions/unmatched'),
        status: 200,
        body: [{ id: 'INT-9', account_id: null, raw_text: 'met with someone new', source_type: 'typed', match_status: 'unmatched', manual_entry_required: false, captured_at: '2026-09-18T00:00:00Z', attendees: [], commitments: [] }],
      },
      { match: (url) => url.endsWith('/accounts'), status: 200, body: [{ id: 'ACC-ACME', name: 'Acme' }] },
      { match: (url) => url.includes('/resolve-customer'), status: 200, body: {} },
    ])
    renderWithProviders(<UnmatchedListPage />)

    expect(await screen.findByText('met with someone new')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Acme' }))
    expect(screen.queryByText('met with someone new')).not.toBeInTheDocument()
  })

  it('shows a retryable error, not a silently-empty picker, when loading accounts fails', async () => {
    mockFetchRoutes([
      {
        match: (url) => url.endsWith('/interactions/unmatched'),
        status: 200,
        body: [{ id: 'INT-9', account_id: null, raw_text: 'met with someone new', source_type: 'typed', match_status: 'unmatched', manual_entry_required: false, captured_at: '2026-09-18T00:00:00Z', attendees: [], commitments: [] }],
      },
      { match: (url) => url.endsWith('/accounts'), status: 503, body: { error_code: 'RETRY_LATER', message: 'The database is briefly busy. Please retry.' } },
    ])
    renderWithProviders(<UnmatchedListPage />)

    expect(await screen.findByText('The database is briefly busy. Please retry.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Search customers')).not.toBeInTheDocument()
  })
})
