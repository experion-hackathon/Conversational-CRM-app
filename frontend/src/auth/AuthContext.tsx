import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { api, ApiError } from '../api/client'

interface AuthContextValue {
  isAuthenticated: boolean
  /** The username typed at login, for display only (e.g. "Welcome back, X") --
   * this app has one shared credential (SEC-1), not per-person accounts, so
   * this is whatever was typed, not a verified individual identity. Resets on
   * reload along with isAuthenticated (see the note below). */
  username: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  /** Any API call that gets a 401 should call this instead of throwing further up unhandled. */
  handleUnauthenticated: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

/**
 * The session itself is an httpOnly cookie (SEC-2) -- this app cannot read it
 * directly, and must not try to. `isAuthenticated` is this tab's own belief
 * about whether login succeeded / a 401 has since been seen; the backend's
 * cookie is the actual source of truth on every request regardless of what
 * this flag says (a stale "true" here just means the next API call 401s and
 * corrects it via handleUnauthenticated).
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [username, setUsername] = useState<string | null>(null)

  const login = useCallback(async (username: string, password: string) => {
    await api.login(username, password)
    setIsAuthenticated(true)
    setUsername(username)
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      setIsAuthenticated(false)
      setUsername(null)
    }
  }, [])

  const handleUnauthenticated = useCallback(() => {
    setIsAuthenticated(false)
    setUsername(null)
  }, [])

  const value = useMemo(
    () => ({ isAuthenticated, username, login, logout, handleUnauthenticated }),
    [isAuthenticated, username, login, logout, handleUnauthenticated],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}

/** Wraps an API call so a 401 updates auth state instead of surfacing as a generic error. */
export function useAuthAwareCall() {
  const { handleUnauthenticated } = useAuth()
  return useCallback(
    async <T,>(call: () => Promise<T>): Promise<T> => {
      try {
        return await call()
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) handleUnauthenticated()
        throw err
      }
    },
    [handleUnauthenticated],
  )
}
