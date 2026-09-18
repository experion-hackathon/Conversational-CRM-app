import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../../api/client'
import type { Commitment } from '../../api/types'
import { useAuth, useAuthAwareCall } from '../../auth/AuthContext'
import { Button } from '../../components/Button'
import { useAccounts } from '../../components/CustomerPicker'
import { EmptyState } from '../../components/EmptyState'
import { InlineErrorBanner } from '../../components/InlineErrorBanner'
import { TextAreaField } from '../../components/TextField'

const HOME_TOP_N = 5
const QUESTION_STARTERS = ['what', 'who', 'when', 'where', 'why', 'how', 'did', 'is', 'are', 'was', 'were']

function looksLikeQuestion(text: string): boolean {
  const trimmed = text.trim().toLowerCase()
  return trimmed.endsWith('?') || QUESTION_STARTERS.some((w) => trimmed.startsWith(w + ' '))
}

/**
 * [INFERRED -- needs confirmation, whole screen] F-8 (US-20..23)'s only design
 * basis is `EXPLORE-UNIFIED-HOME` -- an explicitly ungated, never-validated
 * exploratory canvas concept (workflow-3 ui_ux.json `exploratory_concepts[0]`).
 * Human decision (2026-09-17): build this disclosed as inferred rather than
 * wait for a real UI/UX task. Two backend contract gaps this screen works
 * around rather than papers over (backend report OI-BACKEND-1/2/3):
 *   - No top-N field exists on GET /commitments/due -- "top 5" below is a
 *     client-side slice of the full due list, not a server-side guarantee.
 *   - No distinct "nothing at all yet" (first login) state exists separately
 *     from "nothing due right now" -- both render the same due-commitments
 *     empty message.
 *   - There is no single "unified conversational input" backend operation.
 *     The composer below heuristically routes to POST /qa when the text
 *     looks like a question, else POST /interactions (capture) -- a frontend
 *     guess, not a contract-defined behavior. A misrouted entry is a real,
 *     accepted risk of this heuristic.
 *   - US-22 ("continue the conversation" from a selected item) has no
 *     supporting field on Commitment beyond account_id (disclosed, NOT BUILT
 *     -- OI-BACKEND-2/OI-FRONTEND-4). Items with a known account_id navigate
 *     to the Brief page pre-filled with that customer's name (an existing,
 *     real capability) rather than a purpose-built "resume this thread"
 *     operation that the contract has no field for. Items with no
 *     account_id (unspecified customer) have nothing to navigate to and stay
 *     plain text.
 */
export function HomePage() {
  const authAwareCall = useAuthAwareCall()
  const { username } = useAuth()
  const navigate = useNavigate()
  const { accounts } = useAccounts(api.listAccounts)
  const accountNameById = useMemo(() => new Map(accounts.map((a) => [a.id, a.name])), [accounts])
  const [items, setItems] = useState<Commitment[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [input, setInput] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [feedbackError, setFeedbackError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoadError(null)
    try {
      const response = await authAwareCall(() => api.dueCommitments())
      setItems([...response.overdue, ...response.due_soon])
      setMessage(response.message)
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : 'Could not load your to-do list.')
    } finally {
      setLoading(false)
    }
  }, [authAwareCall])

  useEffect(() => {
    load()
  }, [load])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) return
    setFeedbackError(null)
    setFeedback(null)
    setSubmitting(true)
    try {
      if (looksLikeQuestion(trimmed)) {
        const response = await authAwareCall(() => api.ask(trimmed))
        setFeedback(response.answer_text ?? response.message ?? "Couldn't identify which customer you mean.")
      } else {
        const interaction = await authAwareCall(() => api.captureTyped(trimmed))
        setFeedback(
          interaction.match_status === 'matched'
            ? 'Saved and matched to a customer.'
            : 'Saved — this note needs customer selection (see Notes needing a customer).',
        )
      }
      setInput('')
      load()
    } catch (err) {
      setFeedbackError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: 'var(--space-6)' }}>
      <h1 style={{ fontSize: 'var(--type-scale-xl)' }}>Welcome back{username ? `, ${username}` : ''}</h1>

      {loadError && <InlineErrorBanner message={loadError} onRetry={load} />}
      {loading ? (
        <p aria-live="polite">Loading…</p>
      ) : message ? (
        <EmptyState message={message} />
      ) : (
        <>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {items.slice(0, HOME_TOP_N).map((c) => {
              const customerName = c.account_id ? accountNameById.get(c.account_id) : undefined
              const itemStyle = {
                padding: 'var(--space-3) var(--space-4)',
                border: '1px solid var(--color-border-default)',
                borderRadius: 'var(--radius-card)',
                marginBottom: 'var(--space-3)',
              } as const
              const text = `${c.text} ${c.due_date ? `(due ${c.due_date})` : ''}`

              if (!customerName) {
                return (
                  <li key={c.id} style={itemStyle}>
                    {text}
                  </li>
                )
              }

              return (
                <li key={c.id} style={{ ...itemStyle, padding: 0 }}>
                  <button
                    type="button"
                    onClick={() => navigate('/briefs', { state: { prefillCustomer: customerName } })}
                    title={`See the brief for ${customerName}`}
                    style={{
                      ...itemStyle,
                      width: '100%',
                      textAlign: 'left',
                      background: 'var(--color-bg-surface)',
                      cursor: 'pointer',
                      minHeight: 44,
                    }}
                  >
                    {text}
                  </button>
                </li>
              )
            })}
          </ul>
          {items.length > HOME_TOP_N && <Link to="/commitments">See all {items.length}</Link>}
        </>
      )}

      <form onSubmit={handleSubmit} style={{ marginTop: 'var(--space-8)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <TextAreaField
          label="Capture a note or ask a question"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder='e.g. "Met Priya from Acme" or "What did we discuss last time with Acme?"'
          disabled={submitting}
        />
        {feedbackError && <InlineErrorBanner message={feedbackError} onRetry={() => setFeedbackError(null)} />}
        {feedback && (
          <p role="status" aria-live="polite">
            {feedback}
          </p>
        )}
        <Button type="submit" loading={submitting} disabled={!input.trim()}>
          Send
        </Button>
      </form>
    </main>
  )
}
