import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { api, ApiError } from '../../api/client'
import type { BriefSummary } from '../../api/types'
import { useAuthAwareCall } from '../../auth/AuthContext'
import { Button } from '../../components/Button'
import { EmptyState } from '../../components/EmptyState'
import { InlineErrorBanner } from '../../components/InlineErrorBanner'
import { TextInputField } from '../../components/TextField'

/**
 * [INFERRED -- needs confirmation] No UI/UX design exists for F-5 (US-17..19) -- built directly against POST /briefs's approved contract shape.
 *
 * Also stands in for US-22 ("continue the conversation" from a selected
 * to-do item) within the current contract's real capabilities: the locked
 * API-CONTRACT has no field to carry "which item was clicked" (disclosed,
 * NOT BUILT -- OI-BACKEND-2/OI-FRONTEND-4), so HomePage instead navigates
 * here with the item's customer name pre-filled via router state, reusing
 * this existing brief-by-name flow rather than inventing a new endpoint.
 */
export function BriefPage() {
  const authAwareCall = useAuthAwareCall()
  const location = useLocation()
  const prefillCustomer = (location.state as { prefillCustomer?: string } | null)?.prefillCustomer
  const [requestText, setRequestText] = useState(prefillCustomer ?? '')
  const [summary, setSummary] = useState<BriefSummary | null | undefined>(undefined)
  const [message, setMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const autoSubmitted = useRef(false)

  async function runBrief(text: string) {
    if (!text.trim()) {
      setError('Cannot request a brief with no customer named.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const response = await authAwareCall(() => api.brief(text))
      setSummary(response.summary)
      setMessage(response.message ?? (response.resolution === 'not_identified' ? "Couldn't identify the requested customer." : null))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not generate this brief.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (prefillCustomer && !autoSubmitted.current) {
      autoSubmitted.current = true
      runBrief(prefillCustomer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefillCustomer])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    await runBrief(requestText)
  }

  return (
    <main style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--space-6)' }}>
      <h1 style={{ fontSize: 'var(--type-scale-xl)' }}>Pre-meeting brief</h1>
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
        <div style={{ flex: 1 }}>
          <TextInputField
            label="Brief me on…"
            value={requestText}
            onChange={(e) => setRequestText(e.target.value)}
            placeholder="e.g. brief me on Acme"
          />
        </div>
        <Button type="submit" loading={loading} disabled={!requestText.trim()}>
          Generate
        </Button>
      </form>

      {error && <InlineErrorBanner message={error} onRetry={() => setError(null)} />}
      {message && <EmptyState message={message} />}

      {summary && (
        <article style={{ border: '1px solid var(--color-border-default)', borderRadius: 'var(--radius-card)', padding: 'var(--space-4)' }}>
          {summary.history_text && <p>{summary.history_text}</p>}
          {summary.relationship_status ? (
            <p>
              <strong>Relationship status:</strong> {summary.relationship_status}
            </p>
          ) : (
            <p style={{ color: 'var(--color-text-secondary)' }}>No relationship-status information has been captured yet.</p>
          )}
          {summary.open_commitments.length > 0 && (
            <>
              <h2 style={{ fontSize: 'var(--type-scale-lg)' }}>Open commitments</h2>
              <ul>
                {summary.open_commitments.map((c) => (
                  <li key={c.id}>
                    {c.text} {c.due_date ? `(due ${c.due_date})` : ''}
                  </li>
                ))}
              </ul>
            </>
          )}
          {summary.stakeholders.length > 0 && (
            <>
              <h2 style={{ fontSize: 'var(--type-scale-lg)' }}>Stakeholders</h2>
              <ul>
                {summary.stakeholders.map((s) => (
                  <li key={s.id}>{s.name}</li>
                ))}
              </ul>
            </>
          )}
        </article>
      )}
    </main>
  )
}
