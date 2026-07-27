import { useEffect, useState } from 'react'
import { Link, useLocation, useOutletContext, useParams } from 'react-router'

import { ChatSkeleton } from '@/components/chat/ChatSkeleton'
import type { AppShellContext } from '@/components/layout/AppShell'
import { buttonVariants } from '@/components/ui/button'
import { api, type ChatThreadWithMessages } from '@/lib/api'
import { describeApiError } from '@/lib/chatErrors'
import { ChatConversation } from '@/pages/chat/ChatConversation'

type NewChatState = { firstMessage: string }

export function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>()
  const { refreshThreads } = useOutletContext<AppShellContext>()
  const location = useLocation()
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
        setError(describeApiError(err))
      })
  }, [threadId])

  function handleTurnComplete() {
    refreshThreads()
    if (threadId) api.chat.getThread(threadId).then(setThread)
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 text-muted-foreground">
        <p>{error}</p>
        <Link to="/" className={buttonVariants()}>
          Start a new chat
        </Link>
      </div>
    )
  }

  if (!threadId || !thread) {
    return <ChatSkeleton />
  }

  const state = location.state as NewChatState | null

  return (
    <ChatConversation
      key={thread.id}
      threadId={thread.id}
      title={thread.title}
      initialMessages={thread.messages.map((m) => m.content)}
      autoSendText={state?.firstMessage}
      onTurnComplete={handleTurnComplete}
    />
  )
}
