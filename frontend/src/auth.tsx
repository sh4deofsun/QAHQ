import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, getToken, Me, setToken } from './api'
import { disconnect } from './ws'

interface AuthState {
  user: Me | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  hasPerm: (perm: string) => boolean
}

const AuthContext = createContext<AuthState>(null!)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    await api.login(username, password)
    setUser(await api.me())
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    disconnect()
    setUser(null)
  }, [])

  const hasPerm = useCallback((perm: string) => user?.permissions.includes(perm) ?? false, [user])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, hasPerm }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
