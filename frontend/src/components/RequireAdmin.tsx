import type { ReactNode } from 'react'
import { Navigate } from 'react-router'

import { useAuth } from '@/lib/auth'

/** Nest inside RequireAuth — assumes `loading` has already resolved by the time this renders. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { isAdmin } = useAuth()

  if (!isAdmin) {
    return <Navigate to="/" replace />
  }

  return children
}
