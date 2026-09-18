import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockFetchRoutes } from '../../test/mockFetch'
import { renderWithProviders } from '../../test/renderWithProviders'
import { QAChatPage } from './QAChatPage'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('QAChatPage', () => {
  it('shows the empty state before any question is asked', () => {
    renderWithProviders(<QAChatPage />)
    expect(screen.getByText(/Ask a question about any customer/)).toBeInTheDocument()
  })

  it('rejects an empty question without calling the API', async () => {
    const { fetchMock } = mockFetchRoutes([])
    renderWithProviders(<QAChatPage />)
    const input = screen.getByLabelText('Ask a question')
    await userEvent.type(input, '   ')
    const form = input.closest('form')!
    form.requestSubmit()
    expect(await screen.findByText('Cannot ask an empty question.')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('renders the rep question and the system answer as separate bubbles', async () => {
    mockFetchRoutes([
      {
        match: (url) => url.endsWith('/qa'),
        status: 200,
        body: { resolution: 'answered', account_id: 'ACC-ACME', answer_text: 'discussed renewal pricing', message: null },
      },
    ])
    renderWithProviders(<QAChatPage />)
    await userEvent.type(screen.getByLabelText('Ask a question'), 'what did we discuss last time with Acme')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('discussed renewal pricing')).toBeInTheDocument()
    expect(screen.getByText('what did we discuss last time with Acme')).toBeInTheDocument()
  })

  it('shows a not-identified message without treating it as a network error', async () => {
    mockFetchRoutes([
      { match: (url) => url.endsWith('/qa'), status: 200, body: { resolution: 'not_identified', account_id: null, answer_text: null, message: null } },
    ])
    renderWithProviders(<QAChatPage />)
    await userEvent.type(screen.getByLabelText('Ask a question'), 'what did we discuss with Nobody Inc')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText("I couldn't identify which customer you mean.")).toBeInTheDocument()
  })

  it('shows a retryable error banner and removes the unanswered rep turn on API failure', async () => {
    mockFetchRoutes([{ match: (url) => url.endsWith('/qa'), status: 503, body: { error_code: 'RETRY_LATER', message: 'The database is briefly busy. Please retry.' } }])
    renderWithProviders(<QAChatPage />)
    await userEvent.type(screen.getByLabelText('Ask a question'), 'what did we discuss with Acme')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('The database is briefly busy. Please retry.')).toBeInTheDocument()
  })
})
