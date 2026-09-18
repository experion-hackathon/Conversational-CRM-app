import { useId, type InputHTMLAttributes, type TextareaHTMLAttributes } from 'react'

interface FieldWrapperProps {
  label: string
  error?: string | null
}

/** Multi-line entry per NoteComposer/ChatComposer conventions -- real <label>, error via aria-describedby. */
export function TextAreaField({
  label,
  error,
  ...rest
}: FieldWrapperProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId()
  const errorId = `${id}-error`
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
      <label htmlFor={id} style={{ fontSize: 'var(--type-scale-sm)', color: 'var(--color-text-secondary)' }}>
        {label}
      </label>
      <textarea
        id={id}
        aria-describedby={error ? errorId : undefined}
        aria-invalid={error ? true : undefined}
        style={{
          padding: 'var(--space-3)',
          borderRadius: 'var(--radius-control)',
          border: `1px solid ${error ? 'var(--color-status-danger)' : 'var(--color-border-default)'}`,
          font: 'inherit',
          resize: 'vertical',
          minHeight: 88,
        }}
        {...rest}
      />
      {error && (
        <span id={errorId} role="alert" aria-live="polite" style={{ color: 'var(--color-status-danger)', fontSize: 'var(--type-scale-sm)' }}>
          {error}
        </span>
      )}
    </div>
  )
}

export function TextInputField({
  label,
  error,
  ...rest
}: FieldWrapperProps & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId()
  const errorId = `${id}-error`
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
      <label htmlFor={id} style={{ fontSize: 'var(--type-scale-sm)', color: 'var(--color-text-secondary)' }}>
        {label}
      </label>
      <input
        id={id}
        aria-describedby={error ? errorId : undefined}
        aria-invalid={error ? true : undefined}
        style={{
          padding: 'var(--space-3)',
          borderRadius: 'var(--radius-control)',
          border: `1px solid ${error ? 'var(--color-status-danger)' : 'var(--color-border-default)'}`,
          font: 'inherit',
          minHeight: 44,
        }}
        {...rest}
      />
      {error && (
        <span id={errorId} role="alert" aria-live="polite" style={{ color: 'var(--color-status-danger)', fontSize: 'var(--type-scale-sm)' }}>
          {error}
        </span>
      )}
    </div>
  )
}
