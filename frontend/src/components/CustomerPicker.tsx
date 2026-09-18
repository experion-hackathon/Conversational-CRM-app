import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Account } from '../api/types'
import { TextInputField } from './TextField'

interface CustomerPickerProps {
  accounts: Account[]
  loading?: boolean
  onSelect: (account: Account) => void
}

/** `CustomerPicker` per UI-UX Section 5.2 -- searchable single-select of seeded accounts, reused verbatim across SCR-RESOLVE-UNMATCHED and SCR-QA-CHAT. */
export function CustomerPicker({ accounts, loading = false, onSelect }: CustomerPickerProps) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(
    () => accounts.filter((a) => a.name.toLowerCase().includes(query.toLowerCase())),
    [accounts, query],
  )

  if (loading) return <p aria-live="polite">Loading customers…</p>

  return (
    <div>
      <TextInputField
        label="Search customers"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="e.g. Acme"
      />
      {filtered.length === 0 ? (
        <p style={{ color: 'var(--color-text-secondary)' }}>No customers match "{query}".</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, margin: 'var(--space-2) 0 0' }}>
          {filtered.map((account) => (
            <li key={account.id}>
              <button
                type="button"
                onClick={() => onSelect(account)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: 'var(--space-3)',
                  border: '1px solid var(--color-border-default)',
                  borderRadius: 'var(--radius-control)',
                  background: 'var(--color-bg-surface)',
                  marginBottom: 'var(--space-2)',
                  cursor: 'pointer',
                  minHeight: 44,
                }}
              >
                {account.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Convenience hook wrapping GET /accounts with the same loading/error/retry shape every screen needs. */
export function useAccounts(listAccounts: () => Promise<Account[]>) {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listAccounts()
      .then((result) => {
        if (!cancelled) setAccounts(result)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load customers.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [listAccounts, attempt])

  const retry = useCallback(() => setAttempt((a) => a + 1), [])

  return { accounts, loading, error, retry }
}
