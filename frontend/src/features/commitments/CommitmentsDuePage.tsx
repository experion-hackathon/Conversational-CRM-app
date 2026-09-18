import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../../api/client'
import type { Commitment } from '../../api/types'
import { useAuthAwareCall } from '../../auth/AuthContext'
import { Button } from '../../components/Button'
import { EmptyState } from '../../components/EmptyState'
import { InlineErrorBanner } from '../../components/InlineErrorBanner'

function CommitmentRow({ commitment, onComplete }: { commitment: Commitment; onComplete: (id: string) => void }) {
  return (
    <li
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 'var(--space-3) var(--space-4)',
        border: '1px solid var(--color-border-default)',
        borderRadius: 'var(--radius-card)',
        marginBottom: 'var(--space-3)',
      }}
    >
      <div>
        <p style={{ margin: 0 }}>{commitment.text}</p>
        <p style={{ margin: 0, color: 'var(--color-text-secondary)', fontSize: 'var(--type-scale-sm)' }}>
          {commitment.due_date ? `Due ${commitment.due_date}` : 'No due date given'}
        </p>
      </div>
      <Button variant="secondary" onClick={() => onComplete(commitment.id)}>
        Mark complete
      </Button>
    </li>
  )
}

/**
 * [INFERRED -- needs confirmation] No UI/UX design exists for F-4 (US-15/16)
 * -- built directly against GET /commitments/due's approved contract shape.
 */
export function CommitmentsDuePage() {
  const authAwareCall = useAuthAwareCall()
  const [overdue, setOverdue] = useState<Commitment[]>([])
  const [dueSoon, setDueSoon] = useState<Commitment[]>([])
  const [unspecified, setUnspecified] = useState<Commitment[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    setLoading(true)
    try {
      const response = await authAwareCall(() => api.dueCommitments())
      setOverdue(response.overdue)
      setDueSoon(response.due_soon)
      setUnspecified(response.unspecified)
      setMessage(response.message)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load commitments.')
    } finally {
      setLoading(false)
    }
  }, [authAwareCall])

  useEffect(() => {
    load()
  }, [load])

  async function complete(id: string) {
    try {
      await authAwareCall(() => api.completeCommitment(id))
      setOverdue((prev) => prev.filter((c) => c.id !== id))
      setDueSoon((prev) => prev.filter((c) => c.id !== id))
      setUnspecified((prev) => prev.filter((c) => c.id !== id))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not mark this complete.')
    }
  }

  return (
    <main style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--space-6)' }}>
      <h1 style={{ fontSize: 'var(--type-scale-xl)' }}>Commitments</h1>
      {error && <InlineErrorBanner message={error} onRetry={load} />}
      {loading ? (
        <p aria-live="polite">Loading…</p>
      ) : (
        <>
          {message && <EmptyState message={message} />}
          {overdue.length > 0 && (
            <section>
              <h2 style={{ fontSize: 'var(--type-scale-lg)', color: 'var(--color-status-danger)' }}>Overdue</h2>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {overdue.map((c) => (
                  <CommitmentRow key={c.id} commitment={c} onComplete={complete} />
                ))}
              </ul>
            </section>
          )}
          {dueSoon.length > 0 && (
            <section>
              <h2 style={{ fontSize: 'var(--type-scale-lg)', color: 'var(--color-status-attention-text)' }}>Due soon</h2>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {dueSoon.map((c) => (
                  <CommitmentRow key={c.id} commitment={c} onComplete={complete} />
                ))}
              </ul>
            </section>
          )}
          {unspecified.length > 0 && (
            <section>
              <h2 style={{ fontSize: 'var(--type-scale-lg)', color: 'var(--color-text-secondary)' }}>No due date given</h2>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {unspecified.map((c) => (
                  <CommitmentRow key={c.id} commitment={c} onComplete={complete} />
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  )
}
