import { Plus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'

import { AddConnectionDialog } from '@/components/mcp/AddConnectionDialog'
import { ConnectionRow } from '@/components/mcp/ConnectionRow'
import { Button } from '@/components/ui/button'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Skeleton } from '@/components/ui/skeleton'
import { api, type MCPConnection } from '@/lib/api'

export function ConnectionsPage() {
  const [connections, setConnections] = useState<MCPConnection[] | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()

  const refresh = useCallback(() => {
    api.mcp.listConnections().then(setConnections)
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const oauthResult = searchParams.get('mcp_oauth')

  function dismissOAuthBanner() {
    const next = new URLSearchParams(searchParams)
    next.delete('mcp_oauth')
    setSearchParams(next, { replace: true })
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 p-3">
        <SidebarTrigger />
        <h1 className="text-sm font-semibold text-foreground">MCP connections</h1>
      </div>

      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 overflow-y-auto p-6">
        {oauthResult && (
          <div
            className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
              oauthResult === 'success'
                ? 'border-transparent bg-accent text-accent-foreground'
                : 'border-transparent bg-destructive/10 text-destructive'
            }`}
          >
            <span>
              {oauthResult === 'success'
                ? 'Connection authorized successfully.'
                : "Couldn't complete the OAuth connection. Please try again."}
            </span>
            <button type="button" className="text-xs underline" onClick={dismissOAuthBanner}>
              Dismiss
            </button>
          </div>
        )}

        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            Shared with everyone — connect once, and the assistant can use it in any chat.
          </p>
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="size-4" />
            Add connection
          </Button>
        </div>

        {connections === null ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : connections.length === 0 ? (
          <p className="text-sm text-muted-foreground">No MCP connections yet.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {connections.map((connection) => (
              <ConnectionRow key={connection.id} connection={connection} onChanged={refresh} />
            ))}
          </div>
        )}
      </div>

      <AddConnectionDialog open={dialogOpen} onOpenChange={setDialogOpen} onCreated={refresh} />
    </div>
  )
}
