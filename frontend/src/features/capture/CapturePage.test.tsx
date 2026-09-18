import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockFetchRoutes } from '../../test/mockFetch'
import { renderWithProviders } from '../../test/renderWithProviders'
import { CapturePage } from './CapturePage'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CapturePage', () => {
  it('rejects an empty note with the exact required wording, without calling the API', async () => {
    const { fetchMock } = mockFetchRoutes([])
    renderWithProviders(<CapturePage />)

    const composer = screen.getByLabelText('What happened?')
    await userEvent.click(composer)
    await userEvent.click(screen.getByRole('button', { name: 'Save interaction' }))
    // The button is disabled while the field is empty (per the approved
    // Initial state spec), so directly submit the form to exercise the
    // whitespace-only guard the way a screen reader / programmatic submit would.
    await userEvent.type(composer, '   ')
    const form = composer.closest('form')!
    form.requestSubmit()

    expect(await screen.findByText('Cannot save an empty note.')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows a matched result banner with extracted attendees and commitments on success', async () => {
    mockFetchRoutes([
      {
        match: (url) => url.endsWith('/interactions'),
        status: 201,
        body: {
          id: 'INT-1',
          account_id: 'ACC-ACME',
          raw_text: 'met Priya and Arjun from Acme, demo by Friday',
          source_type: 'typed',
          match_status: 'matched',
          manual_entry_required: false,
          captured_at: '2026-09-18T00:00:00Z',
          attendees: [{ id: 'ATT-1', name: 'Priya', company: 'Acme', role: null }],
          commitments: [{ id: 'CMT-1', account_id: 'ACC-ACME', interaction_id: 'INT-1', text: 'demo', due_date: '2026-09-19', status: 'open' }],
        },
      },
    ])
    renderWithProviders(<CapturePage />)

    await userEvent.type(screen.getByLabelText('What happened?'), 'met Priya and Arjun from Acme, demo by Friday')
    await userEvent.click(screen.getByRole('button', { name: 'Save interaction' }))

    expect(await screen.findByText('Saved and matched to a customer.')).toBeInTheDocument()
    expect(screen.getAllByText(/Priya/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/demo/).length).toBeGreaterThan(0)
  })

  it('shows the customer picker and resolves an unmatched note', async () => {
    mockFetchRoutes([
      {
        match: (url) => url.endsWith('/interactions'),
        status: 201,
        body: {
          id: 'INT-2',
          account_id: null,
          raw_text: 'met with someone, no company named',
          source_type: 'typed',
          match_status: 'unmatched',
          manual_entry_required: false,
          captured_at: '2026-09-18T00:00:00Z',
          attendees: [],
          commitments: [],
        },
      },
      { match: (url) => url.endsWith('/accounts'), status: 200, body: [{ id: 'ACC-ACME', name: 'Acme' }] },
      {
        match: (url) => url.includes('/resolve-customer'),
        status: 200,
        body: {
          id: 'INT-2',
          account_id: 'ACC-ACME',
          raw_text: 'met with someone, no company named',
          source_type: 'typed',
          match_status: 'matched',
          manual_entry_required: false,
          captured_at: '2026-09-18T00:00:00Z',
          attendees: [],
          commitments: [],
        },
      },
    ])
    renderWithProviders(<CapturePage />)

    await userEvent.type(screen.getByLabelText('What happened?'), 'met with someone, no company named')
    await userEvent.click(screen.getByRole('button', { name: 'Save interaction' }))

    expect(await screen.findByText('Saved — needs customer selection.')).toBeInTheDocument()
    await userEvent.click(await screen.findByRole('button', { name: 'Acme' }))

    expect(await screen.findByText('Saved and matched to a customer.')).toBeInTheDocument()
  })

  it('shows a retryable error, not a silently-empty picker, when loading accounts fails', async () => {
    mockFetchRoutes([
      {
        match: (url) => url.endsWith('/interactions'),
        status: 201,
        body: {
          id: 'INT-3',
          account_id: null,
          raw_text: 'met with someone, no company named',
          source_type: 'typed',
          match_status: 'unmatched',
          manual_entry_required: false,
          captured_at: '2026-09-18T00:00:00Z',
          attendees: [],
          commitments: [],
        },
      },
      { match: (url) => url.endsWith('/accounts'), status: 503, body: { error_code: 'RETRY_LATER', message: 'The database is briefly busy. Please retry.' } },
    ])
    renderWithProviders(<CapturePage />)

    await userEvent.type(screen.getByLabelText('What happened?'), 'met with someone, no company named')
    await userEvent.click(screen.getByRole('button', { name: 'Save interaction' }))

    expect(await screen.findByText('The database is briefly busy. Please retry.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Search customers')).not.toBeInTheDocument()
  })
})
