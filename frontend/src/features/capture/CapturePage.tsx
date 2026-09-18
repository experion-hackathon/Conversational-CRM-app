import { useState, type FormEvent } from 'react'
import { api, ApiError } from '../../api/client'
import type { Interaction } from '../../api/types'
import { useAuthAwareCall } from '../../auth/AuthContext'
import { Button } from '../../components/Button'
import { InlineErrorBanner } from '../../components/InlineErrorBanner'
import { TextAreaField } from '../../components/TextField'
import { ResultBanner } from './ResultBanner'

/** SCR-CAPTURE-TEXT (US-1, US-2, US-5, US-6) -- design per UI-UX TASK-CAPTURE-PROFILE Section 4.1. */
export function CapturePage() {
  const authAwareCall = useAuthAwareCall()
  const [mode, setMode] = useState<'typed' | 'card'>('typed')
  const [text, setText] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<Interaction | null>(null)
  const [cardFile, setCardFile] = useState<File | null>(null)

  async function submitTyped(e: FormEvent) {
    e.preventDefault()
    setSubmitError(null)
    if (!text.trim()) {
      // US-2 AC1's exact required wording.
      setFieldError('Cannot save an empty note.')
      return
    }
    setFieldError(null)
    setSubmitting(true)
    try {
      const interaction = await authAwareCall(() => api.captureTyped(text))
      setResult(interaction)
      setText('')
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Couldn't save this note. Try again.")
    } finally {
      setSubmitting(false)
    }
  }

  async function submitCard(e: FormEvent) {
    e.preventDefault()
    if (!cardFile) return
    setSubmitError(null)
    setSubmitting(true)
    try {
      const interaction = await authAwareCall(() => api.captureBusinessCard(cardFile))
      setResult(interaction)
      setCardFile(null)
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Couldn't save this card. Try again.")
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return <ResultBanner interaction={result} onCaptureAnother={() => setResult(null)} />
  }

  return (
    <main style={{ maxWidth: 640, margin: '0 auto', padding: 'var(--space-6)' }}>
      <h1 style={{ fontSize: 'var(--type-scale-xl)' }}>Capture an interaction</h1>

      <div role="tablist" aria-label="Capture mode" style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
        <Button
          type="button"
          variant={mode === 'typed' ? 'primary' : 'secondary'}
          aria-selected={mode === 'typed'}
          role="tab"
          onClick={() => setMode('typed')}
        >
          Type it
        </Button>
        <Button
          type="button"
          variant={mode === 'card' ? 'primary' : 'secondary'}
          aria-selected={mode === 'card'}
          role="tab"
          onClick={() => setMode('card')}
        >
          Scan a business card
        </Button>
      </div>

      {mode === 'typed' ? (
        <form onSubmit={submitTyped} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <TextAreaField
            label="What happened?"
            placeholder='e.g. "Met Priya and Arjun from Acme, discussed renewal pricing, they want a demo of module X by Friday"'
            value={text}
            onChange={(e) => {
              setText(e.target.value)
              if (fieldError) setFieldError(null)
            }}
            error={fieldError}
            disabled={submitting}
          />
          {submitError && <InlineErrorBanner message={submitError} onRetry={() => setSubmitError(null)} />}
          <Button type="submit" loading={submitting} disabled={!text.trim()}>
            Save interaction
          </Button>
        </form>
      ) : (
        <form onSubmit={submitCard} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <label style={{ fontSize: 'var(--type-scale-sm)', color: 'var(--color-text-secondary)' }}>
            Business card image
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setCardFile(e.target.files?.[0] ?? null)}
              style={{ display: 'block', marginTop: 'var(--space-2)' }}
            />
          </label>
          {submitError && <InlineErrorBanner message={submitError} onRetry={() => setSubmitError(null)} />}
          <Button type="submit" loading={submitting} disabled={!cardFile}>
            Save contact
          </Button>
        </form>
      )}
    </main>
  )
}
