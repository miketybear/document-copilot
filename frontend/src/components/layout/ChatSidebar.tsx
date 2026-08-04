import { LogOut, Moon, MoreVertical, Pin, PinOff, Plug, Plus, Sun, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from '@/components/ui/sidebar'
import { ThreadMenuButton } from '@/components/layout/ThreadMenuButton'
import { api, type ChatThread } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'
import { useTheme } from '@/lib/theme'

function groupThreads(threads: ChatThread[]): { label: string; threads: ChatThread[] }[] {
  const startOfToday = new Date()
  startOfToday.setHours(0, 0, 0, 0)

  const pinned: ChatThread[] = []
  const today: ChatThread[] = []
  const earlier: ChatThread[] = []

  // A null title means the thread's first message hasn't finished yet (title is set right when
  // it's sent) — keep it out of the list until then instead of showing a bare "Untitled chat".
  for (const thread of threads) {
    if (thread.title === null) continue

    if (thread.pinned_at) {
      pinned.push(thread)
      continue
    }
    const createdAt = new Date(thread.created_at)
    ;(createdAt >= startOfToday ? today : earlier).push(thread)
  }

  pinned.sort((a, b) => new Date(b.pinned_at!).getTime() - new Date(a.pinned_at!).getTime())

  return [
    { label: 'Pinned', threads: pinned },
    { label: 'Today', threads: today },
    { label: 'Earlier', threads: earlier },
  ].filter((group) => group.threads.length > 0)
}

function initialsFor(email: string | undefined): string {
  if (!email) return '?'
  return email.slice(0, 2).toUpperCase()
}

export function ChatSidebar({
  threads,
  activeThreadId,
  onThreadsChanged,
}: {
  threads: ChatThread[]
  activeThreadId: string | undefined
  onThreadsChanged: () => void
}) {
  const { user } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { isMobile, setOpenMobile } = useSidebar()
  const navigate = useNavigate()
  const [threadPendingDelete, setThreadPendingDelete] = useState<ChatThread | null>(null)

  function closeOnMobile() {
    if (isMobile) setOpenMobile(false)
  }

  async function togglePin(thread: ChatThread) {
    await api.chat.setThreadPinned(thread.id, !thread.pinned_at)
    onThreadsChanged()
  }

  async function confirmDelete() {
    if (!threadPendingDelete) return
    const deletedId = threadPendingDelete.id
    await api.chat.deleteThread(deletedId)
    setThreadPendingDelete(null)
    onThreadsChanged()
    if (deletedId === activeThreadId) navigate('/')
  }

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1.5">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-primary font-mono text-[11px] font-semibold text-primary-foreground">
            DC
          </span>
          <span className="text-sm font-semibold">Document Copilot</span>
        </div>
        <Button
          variant="outline"
          className="justify-start gap-2 font-medium"
          render={<Link to="/" onClick={closeOnMobile} />}
        >
          <Plus className="size-4" />
          New chat
        </Button>
      </SidebarHeader>

      <SidebarContent>
        {groupThreads(threads).map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.threads.map((thread) => (
                  <SidebarMenuItem key={thread.id} className="group/thread">
                    <ThreadMenuButton
                      thread={thread}
                      isActive={thread.id === activeThreadId}
                      onNavigate={closeOnMobile}
                    />

                    <DropdownMenu>
                      <DropdownMenuTrigger
                        render={<SidebarMenuAction showOnHover aria-label="Thread actions" />}
                      >
                        <MoreVertical className="size-4" />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start" side="right">
                        <DropdownMenuItem onClick={() => togglePin(thread)}>
                          {thread.pinned_at ? (
                            <>
                              <PinOff className="size-4" /> Unpin
                            </>
                          ) : (
                            <>
                              <Pin className="size-4" /> Pin
                            </>
                          )}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          variant="destructive"
                          onClick={() => setThreadPendingDelete(thread)}
                        >
                          <Trash2 className="size-4" /> Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        <div className="flex items-center gap-2 px-2 py-1.5 text-xs text-muted-foreground">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent font-mono text-[10px] font-semibold text-accent-foreground">
            {initialsFor(user?.email)}
          </span>
          <span className="flex-1 truncate">{user?.email}</span>
          <Link
            to="/settings/connections"
            aria-label="MCP connections"
            className="text-muted-foreground hover:text-foreground"
            onClick={closeOnMobile}
          >
            <Plug className="size-4" />
          </Link>
          <button
            type="button"
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            className="text-muted-foreground hover:text-foreground"
            onClick={toggleTheme}
          >
            {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
          <button
            type="button"
            aria-label="Sign out"
            className="text-muted-foreground hover:text-foreground"
            onClick={() => supabase.auth.signOut()}
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </SidebarFooter>

      <AlertDialog open={!!threadPendingDelete} onOpenChange={(open) => !open && setThreadPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this chat?</AlertDialogTitle>
            <AlertDialogDescription>
              "{threadPendingDelete?.title ?? 'Untitled chat'}" and all its messages will be permanently
              deleted. This can't be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <SidebarRail />
    </Sidebar>
  )
}
