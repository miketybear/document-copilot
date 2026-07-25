import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type UIMessage } from 'ai'

import { ChatInput } from '@/components/chat/ChatInput'
import { ChatMessageList } from '@/components/chat/ChatMessageList'
import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/http'

export function ChatConversation({
  threadId,
  initialMessages,
}: {
  threadId: string
  initialMessages: UIMessage[]
}) {
  const { messages, sendMessage, status, error } = useChat({
    id: threadId,
    messages: initialMessages,
    transport: new DefaultChatTransport({
      api: `${env.apiBaseUrl}/chat/stream`,
      headers: async () => {
        const token = await getAccessToken()
        return token ? { Authorization: `Bearer ${token}` } : {}
      },
    }),
  })

  return (
    <div className="mx-auto flex min-h-svh max-w-2xl flex-col gap-4 p-4">
      <ChatMessageList messages={messages} />
      {error && <p className="text-sm text-destructive">{error.message}</p>}
      <ChatInput
        disabled={status === 'streaming' || status === 'submitted'}
        onSend={(text) => sendMessage({ text })}
      />
    </div>
  )
}
