import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { Button } from '../components/Button'
import { InlineErrorBanner } from '../components/InlineErrorBanner'
import { TextInputField } from '../components/TextField'
import { useAuth } from './AuthContext'

/**
 * [INFERRED -- needs confirmation] No UI/UX design exists for sign-in: both
 * gated UI/UX tasks explicitly assumed an authenticated session already
 * exists (TASK-CAPTURE-PROFILE Section 2, "Sign-in ... is not itself one of
 * the selected stories"). This screen is built directly against SharedLoginAuth
 * (security_nfr SEC-1, data_integration DAT-10) and the approved token set,
 * since the app cannot function at all without one -- but its layout/copy are
 * this task's own judgment call, not an approved design.
 */
export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(username, password)
      navigate('/', { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.errorCode === 'LOGIN_LOCKED' ? `${err.message} (Retry-After applies -- try again shortly.)` : err.message)
      } else {
        setError('Could not reach the server. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main style={{ maxWidth: 360, margin: '10vh auto', padding: 'var(--space-6)' }}>
      <h1 style={{ fontSize: 'var(--type-scale-xl)' }}>Conversational CRM</h1>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <TextInputField
          label="Username"
          name="username"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <TextInputField
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <InlineErrorBanner message={error} />}
        <Button type="submit" loading={submitting}>
          Sign in
        </Button>
      </form>
    </main>
  )
}
