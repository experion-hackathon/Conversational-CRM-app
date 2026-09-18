import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

/** UI route guards are convenience, never a security boundary (frontend-agent contract) -- the
 * backend's own require_session dependency is the actual authorization check on every request;
 * this only avoids flashing protected UI before that check would fail. */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}
