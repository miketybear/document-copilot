import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type UIMessage } from 'ai'
import { useEffect, useRef } from 'react'

import { ChatInput } from '@/components/chat/ChatInput'
import { ChatMessageList } from '@/components/chat/ChatMessageList'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { describeChatError } from '@/lib/chatErrors'
import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/http'

export function ChatConversation({
  threadId,
  title,
  initialMessages,
  autoSendText,
  onTurnComplete,
}: {
  threadId: string
  title: string | null
  initialMessages: UIMessage[]
  autoSendText?: string
  onTurnComplete?: () => void
}) {
  const { messages, sendMessage, status, error } = useChat({
    id: threadId,
    messages: initialMessages,
    transport: new DefaultChatTransport({
      api: `${env.apiBaseUrl}/chat/stream`,
      headers: async (): Promise<Record<string, string>> => {
        const token = await getAccessToken()
        return token ? { Authorization: `Bearer ${token}` } : {}
      },
    }),
  })

  const hasAutoSent = useRef(false)
  useEffect(() => {
    if (!autoSendText || hasAutoSent.current) return
    hasAutoSent.current = true
    sendMessage({ text: autoSendText })
    // Runs once on mount only — sendMessage/autoSendText intentionally excluded from deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const previousStatus = useRef(status)
  useEffect(() => {
    const wasActive = previousStatus.current === 'submitted' || previousStatus.current === 'streaming'
    previousStatus.current = status
    // The title is set as soon as the first message is sent, before the answer finishes — refresh
    // on 'error' too so a thread whose first turn failed still shows up titled, not stuck hidden.
    if ((status === 'ready' || status === 'error') && wasActive) {
      onTurnComplete?.()
    }
  }, [status, onTurnComplete])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-border px-3 py-3.5 md:px-7">
        <SidebarTrigger className="md:hidden" />
        <h1 className="text-sm font-semibold">{title ?? 'New chat'}</h1>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-2xl flex-col gap-4 p-6">
          <ChatMessageList messages={messages} status={status} />
          {error && <p className="text-sm text-destructive">{describeChatError(error)}</p>}
        </div>
      </div>

      <div className="mx-auto w-full max-w-2xl p-4 pt-0">
        <ChatInput
          disabled={status === 'streaming' || status === 'submitted'}
          onSend={(text) => sendMessage({ text })}
        />
      </div>
    </div>
  )
}
