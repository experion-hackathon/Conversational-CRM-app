import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { Button } from './components/Button'

const NAV_ITEMS = [
  { to: '/', label: 'Home' },
  { to: '/capture', label: 'Capture' },
  { to: '/unmatched', label: 'Unresolved notes' },
  { to: '/ask', label: 'Ask' },
  { to: '/briefs', label: 'Briefs' },
  { to: '/commitments', label: 'Commitments' },
]

export function AppLayout({ children }: { children: ReactNode }) {
  const { logout } = useAuth()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--space-3) var(--space-6)',
          borderBottom: '1px solid var(--color-border-default)',
          background: 'var(--color-bg-surface)',
        }}
      >
        <nav aria-label="Main" style={{ display: 'flex', gap: 'var(--space-4)' }}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              style={({ isActive }) => ({
                color: isActive ? 'var(--color-action-primary)' : 'var(--color-text-primary)',
                fontWeight: isActive ? 600 : 400,
                textDecoration: 'none',
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <Button variant="secondary" onClick={() => logout()}>
          Sign out
        </Button>
      </header>
      <div style={{ flex: 1 }}>{children}</div>
    </div>
  )
}
