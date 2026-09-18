interface ChatMessageBubbleProps {
  role: 'rep' | 'system'
  text: string
  loading?: boolean
}

/** `ChatMessageBubble` per UI-UX TASK-QA-CHAT Section 5.2. */
export function ChatMessageBubble({ role, text, loading = false }: ChatMessageBubbleProps) {
  const isRep = role === 'rep'
  return (
    <div style={{ display: 'flex', justifyContent: isRep ? 'flex-end' : 'flex-start', marginBottom: 'var(--space-3)' }}>
      <div
        aria-live={!isRep ? 'polite' : undefined}
        style={{
          maxWidth: '75%',
          padding: 'var(--space-3) var(--space-4)',
          borderRadius: 'var(--radius-card)',
          background: isRep ? 'var(--color-bg-message-rep)' : 'var(--color-bg-message-system)',
          color: isRep ? 'var(--color-text-oninverse)' : 'var(--color-text-primary)',
          border: isRep ? 'none' : '1px solid var(--color-border-default)',
          whiteSpace: 'pre-wrap',
        }}
      >
        {loading ? 'Thinking…' : text}
      </div>
    </div>
  )
}
