import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth'
import { env } from '@/lib/env'
import { supabase } from '@/lib/supabase'

type BackendStatus = 'checking' | 'ok' | 'unreachable'
type MeState = { id: string; email: string } | 'checking' | 'error'

export function Home() {
  const { session } = useAuth()
  const [status, setStatus] = useState<BackendStatus>('checking')
  const [me, setMe] = useState<MeState>('checking')

  function checkBackend() {
    setStatus('checking')
    fetch(`${env.apiBaseUrl}/health`)
      .then((res) => setStatus(res.ok ? 'ok' : 'unreachable'))
      .catch(() => setStatus('unreachable'))
  }

  function checkMe() {
    if (!session) return
    setMe('checking')
    fetch(`${env.apiBaseUrl}/me`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => setMe(data))
      .catch(() => setMe('error'))
  }

  useEffect(checkBackend, [])
  useEffect(checkMe, [session])

  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-semibold text-foreground">Document Copilot</h1>
      <p className="text-muted-foreground">
        Backend: <span className="font-medium">{status}</span>
      </p>
      <p className="text-muted-foreground">
        /me:{' '}
        <span className="font-medium">
          {me === 'checking' || me === 'error' ? me : `${me.email} (${me.id})`}
        </span>
      </p>
      <div className="flex gap-2">
        <Button onClick={checkBackend}>Recheck backend</Button>
        <Button variant="outline" onClick={() => supabase.auth.signOut()}>
          Sign out
        </Button>
      </div>
    </main>
  )
}
