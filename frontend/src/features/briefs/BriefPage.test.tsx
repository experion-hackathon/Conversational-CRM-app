import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockFetchRoutes } from '../../test/mockFetch'
import { renderWithProviders } from '../../test/renderWithProviders'
import { BriefPage } from './BriefPage'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('BriefPage', () => {
  it('rejects an empty request without calling the API', async () => {
    const { fetchMock } = mockFetchRoutes([])
    renderWithProviders(<BriefPage />)
    const input = screen.getByLabelText('Brief me on…')
    const form = input.closest('form')!
    form.requestSubmit()
    expect(await screen.findByText('Cannot request a brief with no customer named.')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows the no_history message and no summary card', async () => {
    mockFetchRoutes([{ match: (url) => url.endsWith('/briefs'), status: 200, body: { resolution: 'no_history', account_id: 'ACC-GLOBEX', summary: null, message: 'No history exists yet for this customer.' } }])
    renderWithProviders(<BriefPage />)
    await userEvent.type(screen.getByLabelText('Brief me on…'), 'brief me on Globex')
    await userEvent.click(screen.getByRole('button', { name: 'Generate' }))
    expect(await screen.findByText('No history exists yet for this customer.')).toBeInTheDocument()
  })

  it('renders a full summary with commitments and stakeholders', async () => {
    mockFetchRoutes([
      {
        match: (url) => url.endsWith('/briefs'),
        status: 200,
        body: {
          resolution: 'generated',
          account_id: 'ACC-ACME',
          summary: {
            history_text: 'Discussed renewal pricing.',
            open_commitments: [{ id: 'CMT-1', account_id: 'ACC-ACME', interaction_id: 'INT-1', text: 'send pricing sheet', due_date: null, status: 'open' }],
            stakeholders: [{ id: 'ATT-1', name: 'Priya', company: 'Acme', role: null }],
            relationship_status: null,
          },
          message: null,
        },
      },
    ])
    renderWithProviders(<BriefPage />)
    await userEvent.type(screen.getByLabelText('Brief me on…'), 'brief me on Acme')
    await userEvent.click(screen.getByRole('button', { name: 'Generate' }))

    expect(await screen.findByText('Discussed renewal pricing.')).toBeInTheDocument()
    expect(screen.getByText(/send pricing sheet/)).toBeInTheDocument()
    expect(screen.getByText('Priya')).toBeInTheDocument()
    expect(screen.getByText('No relationship-status information has been captured yet.')).toBeInTheDocument()
  })
})
