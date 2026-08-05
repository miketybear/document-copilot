import type { UIMessage } from 'ai'

import { http } from '@/lib/http'

export type ChatThread = {
  id: string
  user_id: string
  title: string | null
  pinned_at: string | null
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

export type MCPConnection = {
  id: string
  name: string
  server_url: string
  auth_type: 'api_token' | 'oauth2'
  status: 'pending' | 'connected' | 'token_expired' | 'error'
  last_error: string | null
  created_by: string
  disabled_tools: string[]
  oauth_client_id: string | null
  oauth_token_endpoint: string | null
  token_expires_at: string | null
  created_at: string
  updated_at: string
}

export type MCPTool = {
  name: string
  description: string | null
  enabled: boolean
}

export const api = {
  ...http,
  chat: {
    listThreads: () => http.get<ChatThread[]>('/chat/threads'),
    createThread: (title?: string) => http.post<ChatThread>('/chat/threads', { title }),
    getThread: (id: string) => http.get<ChatThreadWithMessages>(`/chat/threads/${id}`),
    setThreadPinned: (id: string, pinned: boolean) =>
      http.patch<ChatThread>(`/chat/threads/${id}`, { pinned }),
    deleteThread: (id: string) => http.delete<void>(`/chat/threads/${id}`),
  },
  mcp: {
    listConnections: () => http.get<MCPConnection[]>('/mcp/connections'),
    createApiTokenConnection: (name: string, serverUrl: string, apiToken: string) =>
      http.post<MCPConnection>('/mcp/connections', { name, server_url: serverUrl, api_token: apiToken }),
    startOAuthConnection: (name: string, serverUrl: string) =>
      http.post<{ connection: MCPConnection; authorize_url: string }>('/mcp/connections/oauth', {
        name,
        server_url: serverUrl,
      }),
    deleteConnection: (id: string) => http.delete<void>(`/mcp/connections/${id}`),
    testConnection: (id: string) => http.post<MCPConnection>(`/mcp/connections/${id}/test`),
    listTools: (id: string) => http.get<MCPTool[]>(`/mcp/connections/${id}/tools`),
    setDisabledTools: (id: string, disabledTools: string[]) =>
      http.patch<MCPConnection>(`/mcp/connections/${id}/tools`, { disabled_tools: disabledTools }),
  },
}
