import type { Session, User } from '@supabase/supabase-js'
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import { api } from '@/lib/api'
import { supabase } from '@/lib/supabase'

type AuthContextValue = {
  user: User | null
  session: Session | null
  isAdmin: boolean
  loading: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function syncSession(newSession: Session | null) {
      setSession(newSession)
      if (!newSession) {
        setIsAdmin(false)
        return
      }
      // is_admin isn't part of the Supabase session — it's our own app-level flag, so it needs
      // a round trip to the backend rather than being read off the session object.
      try {
        const me = await api.me()
        if (!cancelled) setIsAdmin(me.is_admin)
      } catch {
        if (!cancelled) setIsAdmin(false)
      }
    }

    supabase.auth.getSession().then(({ data }) => {
      syncSession(data.session).then(() => {
        if (!cancelled) setLoading(false)
      })
    })

    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      syncSession(newSession)
    })

    return () => {
      cancelled = true
      listener.subscription.unsubscribe()
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user: session?.user ?? null, session, isAdmin, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
