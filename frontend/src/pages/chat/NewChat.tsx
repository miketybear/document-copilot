import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router'

import { api } from '@/lib/api'

export function NewChat() {
  const navigate = useNavigate()
  const hasCreated = useRef(false)

  useEffect(() => {
    if (hasCreated.current) return
    hasCreated.current = true

    api.chat.createThread().then((thread) => {
      navigate(`/chat/${thread.id}`, { replace: true })
    })
  }, [navigate])

  return <div className="flex min-h-svh items-center justify-center text-muted-foreground">Loading…</div>
}
