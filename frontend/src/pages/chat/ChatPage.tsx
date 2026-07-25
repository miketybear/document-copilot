import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import { buttonVariants } from '@/components/ui/button'
import { api, type ChatThreadWithMessages } from '@/lib/api'
import { ApiError } from '@/lib/http'
import { ChatConversation } from '@/pages/chat/ChatConversation'

export function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>()
  const [thread, setThread] = useState<ChatThreadWithMessages | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!threadId) return
    setThread(null)
    setError(null)
    api.chat
      .getThread(threadId)
      .then(setThread)
      .catch((err: unknown) => {
        setError(err instanceof ApiError && err.status === 404 ? 'Chat not found.' : 'Failed to load chat.')
      })
  }, [threadId])

  if (error) {
    return (
      <div className="flex min-h-svh flex-col items-center justify-center gap-4 text-muted-foreground">
        <p>{error}</p>
        <Link to="/" className={buttonVariants()}>
          Start a new chat
        </Link>
      </div>
    )
  }

  if (!threadId || !thread) {
    return (
      <div className="flex min-h-svh items-center justify-center text-muted-foreground">Loading…</div>
    )
  }

  return (
    <ChatConversation
      key={thread.id}
      threadId={thread.id}
      initialMessages={thread.messages.map((m) => m.content)}
    />
  )
}
