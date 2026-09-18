import type { ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary'
  loading?: boolean
}

/** Primary/secondary action button per the approved token set (color.action.primary). */
export function Button({ variant = 'primary', loading = false, disabled, children, style, ...rest }: ButtonProps) {
  const isPrimary = variant === 'primary'
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      style={{
        padding: 'var(--space-2) var(--space-4)',
        borderRadius: 'var(--radius-control)',
        border: isPrimary ? 'none' : '1px solid var(--color-border-default)',
        background: isPrimary ? 'var(--color-action-primary)' : 'var(--color-bg-surface)',
        color: isPrimary ? 'var(--color-text-oninverse)' : 'var(--color-text-primary)',
        fontSize: 'var(--type-scale-base)',
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled || loading ? 0.6 : 1,
        minHeight: 44,
        ...style,
      }}
    >
      {loading ? 'Working…' : children}
    </button>
  )
}
