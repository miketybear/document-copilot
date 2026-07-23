import type { ReactNode } from 'react'
import { Navigate } from 'react-router'

import { useAuth } from '@/lib/auth'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return null
  }

  if (!user) {
    return <Navigate to="/sign-in" replace />
  }

  return children
}
