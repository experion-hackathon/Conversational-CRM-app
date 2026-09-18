import { Button } from './Button'

interface InlineErrorBannerProps {
  message: string
  onRetry?: () => void
}

/** `InlineErrorBanner` per UI-UX Section 5.2 -- recoverable failure + Retry, aria-live announced. */
export function InlineErrorBanner({ message, onRetry }: InlineErrorBannerProps) {
  return (
    <div
      role="alert"
      aria-live="polite"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 'var(--space-3)',
        padding: 'var(--space-3) var(--space-4)',
        borderRadius: 'var(--radius-card)',
        border: '1px solid var(--color-status-danger)',
        background: '#fdecea',
        color: 'var(--color-status-danger)',
      }}
    >
      <span>{message}</span>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry} type="button">
          Retry
        </Button>
      )}
    </div>
  )
}
