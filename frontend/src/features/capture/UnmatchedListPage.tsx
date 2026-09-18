import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../../api/client'
import type { Interaction } from '../../api/types'
import { useAuthAwareCall } from '../../auth/AuthContext'
import { CustomerPicker, useAccounts } from '../../components/CustomerPicker'
import { EmptyState } from '../../components/EmptyState'
import { InlineErrorBanner } from '../../components/InlineErrorBanner'

/**
 * [INFERRED -- needs confirmation] UI-UX's own Open Item OI-4: "no story
 * defines where a rep finds a previously-unresolved note." GET
 * /interactions/unmatched already exists on the backend for exactly this;
 * this screen is this task's own reasonable placement of it, not an
 * approved design.
 */
export function UnmatchedListPage() {
  const authAwareCall = useAuthAwareCall()
  const [items, setItems] = useState<Interaction[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const listAccounts = useCallback(() => api.listAccounts(), [])
  const { accounts, loading: accountsLoading, error: accountsError, retry: retryAccounts } = useAccounts(listAccounts)

  const load = useCallback(async () => {
    setLoadError(null)
    try {
      const result = await authAwareCall(() => api.listUnmatched())
      setItems(result)
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : 'Could not load unmatched notes.')
    }
  }, [authAwareCall])

  useEffect(() => {
    load()
  }, [load])

  async function resolve(id: string, accountId: string) {
    try {
      await authAwareCall(() => api.resolveCustomer(id, accountId))
      setItems((prev) => (prev ? prev.filter((i) => i.id !== id) : prev))
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : 'Could not resolve this note.')
    }
  }

  return (
    <main style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--space-6)' }}>
      <h1 style={{ fontSize: 'var(--type-scale-xl)' }}>Notes needing a customer</h1>
      {loadError && <InlineErrorBanner message={loadError} onRetry={load} />}
      {accountsError && <InlineErrorBanner message={accountsError} onRetry={retryAccounts} />}
      {items === null ? (
        <p aria-live="polite">Loading…</p>
      ) : items.length === 0 ? (
        <EmptyState message="Nothing needs customer selection right now." />
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {items.map((item) => (
            <li
              key={item.id}
              style={{
                border: '1px solid var(--color-border-default)',
                borderRadius: 'var(--radius-card)',
                padding: 'var(--space-4)',
                marginBottom: 'var(--space-4)',
              }}
            >
              <p style={{ color: 'var(--color-text-secondary)' }}>{item.raw_text}</p>
              {!accountsError && <CustomerPicker accounts={accounts} loading={accountsLoading} onSelect={(a) => resolve(item.id, a.id)} />}
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}
