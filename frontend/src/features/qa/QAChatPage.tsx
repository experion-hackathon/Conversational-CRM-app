import { useState, type FormEvent } from 'react'
import { api, ApiError } from '../../api/client'
import { useAuthAwareCall } from '../../auth/AuthContext'
import { Button } from '../../components/Button'
import { EmptyState } from '../../components/EmptyState'
import { InlineErrorBanner } from '../../components/InlineErrorBanner'
import { TextInputField } from '../../components/TextField'
import { ChatMessageBubble } from './ChatMessageBubble'

interface Turn {
  role: 'rep' | 'system'
  text: string
}

const SUGGESTIONS = ['What did we discuss last time with Acme?', 'What did I commit to for Globex?', 'Who attended from Initech’s side?']

/** SCR-QA-CHAT (US-9..US-14) -- design per UI-UX TASK-QA-CHAT Section 4. */
export function QAChatPage() {
  const authAwareCall = useAuthAwareCall()
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function ask(text: string) {
    const trimmed = text.trim()
    if (!trimmed) {
      setError('Cannot ask an empty question.')
      return
    }
    setError(null)
    setTurns((prev) => [...prev, { role: 'rep', text: trimmed }])
    setQuestion('')
    setAsking(true)
    try {
      const response = await authAwareCall(() => api.ask(trimmed))
      const answer =
        response.resolution === 'not_identified'
          ? "I couldn't identify which customer you mean."
          : (response.answer_text ?? response.message ?? 'No answer available.')
      setTurns((prev) => [...prev, { role: 'system', text: answer }])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the assistant. Try again.")
      setTurns((prev) => prev.slice(0, -1))
    } finally {
      setAsking(false)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    ask(question)
  }

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <h1 style={{ fontSize: 'var(--type-scale-xl)' }}>Ask about a customer</h1>

      <div style={{ flex: 1, overflowY: 'auto', marginBottom: 'var(--space-4)' }}>
        {turns.length === 0 ? (
          <EmptyState message="Ask a question about any customer's history, commitments, or attendees." />
        ) : (
          turns.map((turn, i) => <ChatMessageBubble key={i} role={turn.role} text={turn.text} />)
        )}
        {asking && <ChatMessageBubble role="system" text="" loading />}
      </div>

      {error && <InlineErrorBanner message={error} onRetry={() => setError(null)} />}

      {turns.length === 0 && (
        <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', marginBottom: 'var(--space-3)' }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => ask(s)}
              style={{
                padding: 'var(--space-2) var(--space-3)',
                borderRadius: 'var(--radius-control)',
                border: '1px solid var(--color-border-default)',
                background: 'var(--color-bg-surface)',
                cursor: 'pointer',
              }}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 'var(--space-2)' }}>
        <div style={{ flex: 1 }}>
          <TextInputField
            label="Ask a question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={asking}
            placeholder="What did we discuss last time with…"
          />
        </div>
        <Button type="submit" loading={asking} disabled={!question.trim()}>
          Send
        </Button>
      </form>
    </main>
  )
}
