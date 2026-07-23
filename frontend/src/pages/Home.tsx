import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { env } from '@/lib/env'

type BackendStatus = 'checking' | 'ok' | 'unreachable'

export function Home() {
  const [status, setStatus] = useState<BackendStatus>('checking')

  function checkBackend() {
    setStatus('checking')
    fetch(`${env.apiBaseUrl}/health`)
      .then((res) => setStatus(res.ok ? 'ok' : 'unreachable'))
      .catch(() => setStatus('unreachable'))
  }

  useEffect(checkBackend, [])

  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-semibold text-foreground">Document Copilot</h1>
      <p className="text-muted-foreground">
        Backend: <span className="font-medium">{status}</span>
      </p>
      <Button onClick={checkBackend}>Recheck backend</Button>
    </main>
  )
}
