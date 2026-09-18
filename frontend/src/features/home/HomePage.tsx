import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../../api/client'
import type { Commitment } from '../../api/types'
import { useAuthAwareCall } from '../../auth/AuthContext'
import { Button } from '../../components/Button'
import { useAccounts } from '../../components/CustomerPicker'
import { EmptyState } from '../../components/EmptyState'
import { InlineErrorBanner } from '../../components/InlineErrorBanner'
import { TextAreaField } from '../../components/TextField'
import { ChatMessageBubble } from '../qa/ChatMessageBubble'

const HOME_TOP_N = 5
const QUESTION_STARTERS = ['what', 'who', 'when', 'where', 'why', 'how', 'did', 'is', 'are', 'was', 'were']
const SUGGESTIONS = ['What do I need to follow up on today?', 'What did I discuss with Acme last time?']

function looksLikeQuestion(text: string): boolean {
  const trimmed = text.trim().toLowerCase()
  return trimmed.endsWith('?') || QUESTION_STARTERS.some((w) => trimmed.startsWith(w + ' '))
}

/** "Due tomorrow" / "Overdue by 3 days" / "Due in 3 days" -- client-side only, from due_date vs today. */
function formatDueLabel(dueDate: string | null, bucket: 'overdue' | 'due_soon'): string {
  if (!dueDate) return bucket === 'overdue' ? 'Overdue' : 'Due soon'
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(`${dueDate}T00:00:00`)
  const diffDays = Math.round((due.getTime() - today.getTime()) / 86_400_000)
  if (diffDays === 0) return 'Due today'
  if (diffDays === 1) return 'Due tomorrow'
  if (diffDays > 1) return `Due in ${diffDays} days`
  const overdueDays = Math.abs(diffDays)
  return overdueDays === 1 ? 'Overdue by 1 day' : `Overdue by ${overdueDays} days`
}

interface TodoItem extends Commitment {
  bucket: 'overdue' | 'due_soon'
}

interface Turn {
  role: 'rep' | 'system'
  text: string
}

/**
 * [INFERRED -- needs confirmation, whole screen] F-8 (US-20..23)'s only design
 * basis is `EXPLORE-UNIFIED-HOME` -- an explicitly ungated, never-validated
 * exploratory canvas concept (workflow-3 ui_ux.json `exploratory_concepts[0]`).
 * Human decision (2026-09-17): build this disclosed as inferred rather than
 * wait for a real UI/UX task. Redesigned into a two-pane assistant layout on
 * explicit human request (2026-09-18), reusing `ChatMessageBubble` verbatim
 * from the one approved chat surface this product has (TASK-QA-CHAT), rather
 * than inventing new chat-bubble styling for this ungated screen. Backend
 * contract gaps this screen works around rather than papers over (backend
 * report OI-BACKEND-1/2/3):
 *   - No top-N field exists on GET /commitments/due -- "top 5" below is a
 *     client-side slice of the full due list, not a server-side guarantee.
 *   - No distinct "nothing at all yet" (first login) state exists separately
 *     from "nothing due right now" -- both render the same due-commitments
 *     empty message.
 *   - There is no single "unified conversational input" backend operation.
 *     The composer heuristically routes to POST /qa when the text looks like
 *     a question, else POST /interactions (capture) -- a frontend guess, not
 *     a contract-defined behavior. A misrouted entry is a real, accepted risk.
 *   - US-22 ("continue the conversation" from a selected item) has no
 *     supporting field on Commitment beyond account_id (disclosed, NOT BUILT
 *     -- OI-BACKEND-2/OI-FRONTEND-4). Cards with a known account_id navigate
 *     to the Brief page pre-filled with that customer's name (an existing,
 *     real capability) rather than a purpose-built "resume this thread"
 *     operation the contract has no field for. Cards with no account_id
 *     (unspecified customer) have nothing to navigate to and are not clickable.
 */
export function HomePage() {
  const authAwareCall = useAuthAwareCall()
  const navigate = useNavigate()
  const { accounts } = useAccounts(api.listAccounts)
  const accountNameById = useMemo(() => new Map(accounts.map((a) => [a.id, a.name])), [accounts])

  const [overdue, setOverdue] = useState<Commitment[]>([])
  const [dueSoon, setDueSoon] = useState<Commitment[]>([])
  const [emptyMessage, setEmptyMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [input, setInput] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [turns, setTurns] = useState<Turn[]>([
    {
      role: 'system',
      text: "Hi, welcome back. Here's what's on your plate today — tap anything on the left to dig in, or just tell me what happened.",
    },
  ])
  const [feedbackError, setFeedbackError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoadError(null)
    try {
      const response = await authAwareCall(() => api.dueCommitments())
      setOverdue(response.overdue)
      setDueSoon(response.due_soon)
      setEmptyMessage(response.message)
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : 'Could not load your to-do list.')
    } finally {
      setLoading(false)
    }
  }, [authAwareCall])

  useEffect(() => {
    load()
  }, [load])

  const todoItems: TodoItem[] = useMemo(
    () => [...overdue.map((c) => ({ ...c, bucket: 'overdue' as const })), ...dueSoon.map((c) => ({ ...c, bucket: 'due_soon' as const }))],
    [overdue, dueSoon],
  )
  const visibleItems = todoItems.slice(0, HOME_TOP_N)
  const remainingCount = todoItems.length - visibleItems.length

  async function send(text: string) {
    const trimmed = text.trim()
    if (!trimmed) return
    setFeedbackError(null)
    setTurns((prev) => [...prev, { role: 'rep', text: trimmed }])
    setInput('')
    setSubmitting(true)
    try {
      if (looksLikeQuestion(trimmed)) {
        const response = await authAwareCall(() => api.ask(trimmed))
        const answer = response.resolution === 'not_identified' ? "Couldn't identify which customer you mean." : (response.answer_text ?? response.message ?? 'No answer available.')
        setTurns((prev) => [...prev, { role: 'system', text: answer }])
      } else {
        const interaction = await authAwareCall(() => api.captureTyped(trimmed))
        setTurns((prev) => [
          ...prev,
          {
            role: 'system',
            text:
              interaction.match_status === 'matched'
                ? 'Saved and matched to a customer.'
                : 'Saved — this note needs customer selection (see Notes needing a customer).',
          },
        ])
        load()
      }
    } catch (err) {
      setFeedbackError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
      setTurns((prev) => prev.slice(0, -1))
    } finally {
      setSubmitting(false)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    send(input)
  }

  return (
    <div style={{ display: 'flex', height: '100%', minHeight: 'calc(100vh - 57px)' }}>
      <aside
        style={{
          width: 320,
          flexShrink: 0,
          borderRight: '1px solid var(--color-border-default)',
          padding: 'var(--space-6) var(--space-4)',
          overflowY: 'auto',
        }}
      >
        <h2 style={{ fontSize: 'var(--type-scale-lg)', margin: 0 }}>To-do &amp; activities</h2>
        <p style={{ fontSize: 'var(--type-scale-sm)', color: 'var(--color-text-secondary)', marginTop: 'var(--space-1)' }}>
          Top priorities — tap one to dig in
        </p>

        {loadError && <InlineErrorBanner message={loadError} onRetry={load} />}
        {loading ? (
          <p aria-live="polite">Loading…</p>
        ) : emptyMessage ? (
          <EmptyState message={emptyMessage} />
        ) : (
          <>
            <ul style={{ listStyle: 'none', padding: 0, margin: 'var(--space-4) 0 0' }}>
              {visibleItems.map((item) => {
                const customerName = item.account_id ? accountNameById.get(item.account_id) : undefined
                const isOverdue = item.bucket === 'overdue'
                const badge = (
                  <span
                    style={{
                      fontSize: 'var(--type-scale-xs)',
                      fontWeight: 700,
                      letterSpacing: '0.02em',
                      padding: '2px var(--space-2)',
                      borderRadius: 999,
                      color: isOverdue ? 'var(--color-status-danger)' : 'var(--color-status-attention-text)',
                      // No approved "danger background" token exists (only --color-status-attention-bg for amber) --
                      // derived via color-mix from the approved --color-status-danger text color instead of inventing a hex value.
                      background: isOverdue ? 'color-mix(in srgb, var(--color-status-danger) 12%, white)' : 'var(--color-status-attention-bg)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {isOverdue ? 'OVERDUE' : 'DUE SOON'}
                  </span>
                )
                const cardStyle = {
                  display: 'block',
                  width: '100%',
                  textAlign: 'left' as const,
                  padding: 'var(--space-3)',
                  border: '1px solid var(--color-border-default)',
                  borderRadius: 'var(--radius-card)',
                  marginBottom: 'var(--space-3)',
                  background: 'var(--color-bg-surface)',
                }

                const inner = (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--space-2)' }}>
                      <strong style={{ fontSize: 'var(--type-scale-sm)' }}>{customerName ?? 'Unspecified customer'}</strong>
                      {badge}
                    </div>
                    <p style={{ margin: 'var(--space-1) 0 0', fontSize: 'var(--type-scale-sm)' }}>{item.text}</p>
                    <p style={{ margin: 'var(--space-1) 0 0', fontSize: 'var(--type-scale-xs)', color: 'var(--color-text-secondary)' }}>
                      {formatDueLabel(item.due_date, item.bucket)}
                    </p>
                  </>
                )

                return (
                  <li key={item.id}>
                    {customerName ? (
                      <button
                        type="button"
                        onClick={() => navigate('/briefs', { state: { prefillCustomer: customerName } })}
                        title={`See the brief for ${customerName}`}
                        style={{ ...cardStyle, cursor: 'pointer', minHeight: 44 }}
                      >
                        {inner}
                      </button>
                    ) : (
                      <div style={cardStyle}>{inner}</div>
                    )}
                  </li>
                )
              })}
            </ul>
            {remainingCount > 0 && (
              <Link to="/commitments" style={{ fontSize: 'var(--type-scale-sm)' }}>
                More (+{remainingCount})
              </Link>
            )}
          </>
        )}
      </aside>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 'var(--space-6)', minWidth: 0 }}>
        {/* Hardcoded display name: this app has one shared login (SEC-1), no per-person accounts to derive a real name from. */}
        <h1 style={{ fontSize: 'var(--type-scale-xl)', margin: 0 }}>Welcome, John Doe</h1>
        <p style={{ color: 'var(--color-text-secondary)', marginTop: 'var(--space-1)' }}>Here's what needs your attention today.</p>

        <div style={{ flex: 1, overflowY: 'auto', margin: 'var(--space-4) 0' }}>
          {turns.map((turn, i) => (
            <ChatMessageBubble key={i} role={turn.role} text={turn.text} />
          ))}
          {submitting && <ChatMessageBubble role="system" text="" loading />}
        </div>

        {feedbackError && <InlineErrorBanner message={feedbackError} onRetry={() => setFeedbackError(null)} />}

        {turns.length === 1 && (
          <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', marginBottom: 'var(--space-3)' }}>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => send(s)}
                disabled={submitting}
                style={{
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-control)',
                  border: '1px solid var(--color-border-default)',
                  background: 'var(--color-bg-surface)',
                  cursor: 'pointer',
                  fontSize: 'var(--type-scale-sm)',
                }}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <TextAreaField
            label="Capture a note or ask a question"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='e.g. "hello, I met with a new customer today named Geoffrey from Acme..."'
            disabled={submitting}
          />
          <Button type="submit" loading={submitting} disabled={!input.trim()}>
            Send
          </Button>
        </form>
      </main>
    </div>
  )
}
