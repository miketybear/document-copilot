import type { UIMessage } from 'ai'

import { http } from '@/lib/http'

export type ChatThread = {
  id: string
  user_id: string
  title: string | null
  created_at: string
  updated_at: string
}

export type ChatMessageRow = {
  id: string
  thread_id: string
  role: 'user' | 'assistant' | 'system'
  content: UIMessage
  created_at: string
}

export type ChatThreadWithMessages = ChatThread & {
  messages: ChatMessageRow[]
}

export const api = {
  ...http,
  chat: {
    listThreads: () => http.get<ChatThread[]>('/chat/threads'),
    createThread: (title?: string) => http.post<ChatThread>('/chat/threads', { title }),
    getThread: (id: string) => http.get<ChatThreadWithMessages>(`/chat/threads/${id}`),
  },
}
