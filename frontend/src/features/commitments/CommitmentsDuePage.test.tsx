import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockFetchRoutes } from '../../test/mockFetch'
import { renderWithProviders } from '../../test/renderWithProviders'
import { CommitmentsDuePage } from './CommitmentsDuePage'

afterEach(() => {
  vi.restoreAllMocks()
})

const commitment = {
  id: 'CMT-1',
  account_id: 'ACC-ACME',
  interaction_id: 'INT-1',
  text: 'send pricing sheet',
  due_date: '2026-09-10',
  status: 'open' as const,
}

describe('CommitmentsDuePage', () => {
  it('shows the explicit empty-state message when nothing is due', async () => {
    mockFetchRoutes([{ match: (url) => url.includes('/commitments/due'), status: 200, body: { overdue: [], due_soon: [], unspecified: [], message: 'There are no due-soon or overdue commitments right now.' } }])
    renderWithProviders(<CommitmentsDuePage />)
    expect(await screen.findByText('There are no due-soon or overdue commitments right now.')).toBeInTheDocument()
  })

  it('lists overdue commitments under their own heading', async () => {
    mockFetchRoutes([{ match: (url) => url.includes('/commitments/due'), status: 200, body: { overdue: [commitment], due_soon: [], unspecified: [], message: null } }])
    renderWithProviders(<CommitmentsDuePage />)
    expect(await screen.findByRole('heading', { name: 'Overdue' })).toBeInTheDocument()
    expect(screen.getByText('send pricing sheet')).toBeInTheDocument()
  })

  it('removes a commitment from the list after marking it complete', async () => {
    mockFetchRoutes([
      { match: (url) => url.includes('/commitments/due'), status: 200, body: { overdue: [commitment], due_soon: [], unspecified: [], message: null } },
      { match: (url) => url.includes('/complete'), status: 200, body: { ...commitment, status: 'complete' } },
    ])
    renderWithProviders(<CommitmentsDuePage />)
    await screen.findByText('send pricing sheet')
    await userEvent.click(screen.getByRole('button', { name: 'Mark complete' }))
    expect(screen.queryByText('send pricing sheet')).not.toBeInTheDocument()
  })

  it('shows a retryable error banner when loading fails', async () => {
    mockFetchRoutes([{ match: (url) => url.includes('/commitments/due'), status: 503, body: { error_code: 'RETRY_LATER', message: 'The database is briefly busy. Please retry.' } }])
    renderWithProviders(<CommitmentsDuePage />)
    expect(await screen.findByText('The database is briefly busy. Please retry.')).toBeInTheDocument()
  })
})
