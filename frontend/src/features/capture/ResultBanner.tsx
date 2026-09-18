import { useCallback, useState } from 'react'
import { api, ApiError } from '../../api/client'
import type { Interaction } from '../../api/types'
import { useAuthAwareCall } from '../../auth/AuthContext'
import { Button } from '../../components/Button'
import { CustomerPicker, useAccounts } from '../../components/CustomerPicker'
import { InlineErrorBanner } from '../../components/InlineErrorBanner'

interface ResultBannerProps {
  interaction: Interaction
  onCaptureAnother: () => void
}

/**
 * `ResultBanner` (SCR-CAPTURE-RESULT, US-1/US-2) folded together with
 * `SCR-RESOLVE-UNMATCHED` (US-3) as one inline flow when unmatched, per the
 * approved flowchart's S3U -> S4 transition. Also surfaces extracted
 * attendees/commitments (F-2, US-5/US-7/US-8/US-9) -- this display was not
 * in TASK-CAPTURE-PROFILE's original scope (F-2 was explicitly excluded,
 * Section 2), but the backend now returns this data on every capture
 * response, and showing it is a direct, low-risk extension of the approved
 * InteractionCard concept. [INFERRED -- needs confirmation]
 */
export function ResultBanner({ interaction, onCaptureAnother }: ResultBannerProps) {
  const authAwareCall = useAuthAwareCall()
  const listAccounts = useCallback(() => api.listAccounts(), [])
  const { accounts, loading: accountsLoading, error: accountsError, retry: retryAccounts } = useAccounts(listAccounts)
  const [resolved, setResolved] = useState(interaction)
  const [resolveError, setResolveError] = useState<string | null>(null)
  const [resolving, setResolving] = useState(false)

  async function handleResolve(accountId: string) {
    setResolveError(null)
    setResolving(true)
    try {
      const updated = await authAwareCall(() => api.resolveCustomer(interaction.id, accountId))
      setResolved(updated)
    } catch (err) {
      setResolveError(err instanceof ApiError ? err.message : 'Could not resolve this note. Try again.')
    } finally {
      setResolving(false)
    }
  }

  const isMatched = resolved.match_status === 'matched'

  return (
    <main style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--space-6)' }}>
      <div
        role="status"
        style={{
          padding: 'var(--space-4)',
          borderRadius: 'var(--radius-card)',
          background: isMatched ? '#e6f4ea' : 'var(--color-status-attention-bg)',
          color: isMatched ? 'var(--color-status-success)' : 'var(--color-status-attention-text)',
          marginBottom: 'var(--space-4)',
        }}
      >
        {isMatched ? 'Saved and matched to a customer.' : 'Saved — needs customer selection.'}
      </div>

      <blockquote style={{ margin: 0, marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)' }}>
        {resolved.raw_text}
      </blockquote>

      {resolved.attendees.length > 0 && (
        <p>
          <strong>Attendees:</strong> {resolved.attendees.map((a) => a.name).join(', ')}
        </p>
      )}
      {resolved.commitments.length > 0 && (
        <ul>
          {resolved.commitments.map((c) => (
            <li key={c.id}>
              {c.text} {c.due_date ? `(due ${c.due_date})` : '(no due date given)'}
            </li>
          ))}
        </ul>
      )}

      {!isMatched && (
        <div style={{ marginTop: 'var(--space-4)' }}>
          <h2 style={{ fontSize: 'var(--type-scale-lg)' }}>Which customer is this?</h2>
          {resolveError && <InlineErrorBanner message={resolveError} onRetry={() => setResolveError(null)} />}
          {accountsError && <InlineErrorBanner message={accountsError} onRetry={retryAccounts} />}
          {resolving ? (
            <p aria-live="polite">Resolving…</p>
          ) : (
            !accountsError && <CustomerPicker accounts={accounts} loading={accountsLoading} onSelect={(a) => handleResolve(a.id)} />
          )}
        </div>
      )}

      <div style={{ marginTop: 'var(--space-6)' }}>
        <Button variant="secondary" onClick={onCaptureAnother}>
          Capture another
        </Button>
      </div>
    </main>
  )
}
