import type { ReactNode } from 'react'

interface EmptyStateProps {
  message: string
  action?: ReactNode
}

/** `EmptyState` per UI-UX Section 5.2 -- explicit "nothing here yet" message, never a blank screen. */
export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div
      style={{
        padding: 'var(--space-8)',
        textAlign: 'center',
        color: 'var(--color-text-secondary)',
        borderRadius: 'var(--radius-card)',
        border: '1px dashed var(--color-border-default)',
      }}
    >
      <p>{message}</p>
      {action}
    </div>
  )
}
