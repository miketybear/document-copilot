import { useCallback, useEffect, useState } from 'react'
import { Outlet, useParams } from 'react-router'

import { ChatSidebar } from '@/components/layout/ChatSidebar'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { api, type ChatThread } from '@/lib/api'

export type AppShellContext = {
  refreshThreads: () => void
}

export function AppShell() {
  const { threadId } = useParams<{ threadId: string }>()
  const [threads, setThreads] = useState<ChatThread[]>([])

  const refreshThreads = useCallback(() => {
    api.chat.listThreads().then(setThreads)
  }, [])

  useEffect(() => {
    refreshThreads()
  }, [threadId, refreshThreads])

  return (
    <SidebarProvider className="h-svh">
      <ChatSidebar threads={threads} activeThreadId={threadId} onThreadsChanged={refreshThreads} />
      <SidebarInset>
        <Outlet context={{ refreshThreads } satisfies AppShellContext} />
      </SidebarInset>
    </SidebarProvider>
  )
}
