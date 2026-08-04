import { MoreVertical, RefreshCw, Trash2 } from 'lucide-react'
import { useState } from 'react'

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
import { Badge, type badgeVariants } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { api, type MCPConnection } from '@/lib/api'
import { describeApiError } from '@/lib/chatErrors'
import type { VariantProps } from 'class-variance-authority'

const STATUS_LABEL: Record<MCPConnection['status'], string> = {
  connected: 'Connected',
  pending: 'Pending authorization',
  token_expired: 'Token expired',
  error: 'Error',
}

const STATUS_VARIANT: Record<MCPConnection['status'], NonNullable<VariantProps<typeof badgeVariants>['variant']>> = {
  connected: 'success',
  pending: 'default',
  token_expired: 'warning',
  error: 'destructive',
}

export function ConnectionRow({ connection, onChanged }: { connection: MCPConnection; onChanged: () => void }) {
  const [testing, setTesting] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [testError, setTestError] = useState<string | null>(null)

  async function handleTest() {
    setTesting(true)
    setTestError(null)
    try {
      await api.mcp.testConnection(connection.id)
      onChanged()
    } catch (err) {
      setTestError(describeApiError(err))
    } finally {
      setTesting(false)
    }
  }

  async function handleDelete() {
    await api.mcp.deleteConnection(connection.id)
    setConfirmingDelete(false)
    onChanged()
  }

  const authTypeLabel = connection.auth_type === 'api_token' ? 'API token' : 'OAuth 2.x'

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card p-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate font-medium text-foreground">{connection.name}</span>
          <Badge variant={STATUS_VARIANT[connection.status]}>{STATUS_LABEL[connection.status]}</Badge>
          <span className="text-xs text-muted-foreground">{authTypeLabel}</span>
        </div>
        <p className="truncate text-xs text-muted-foreground">{connection.server_url}</p>
        {(connection.last_error ?? testError) && (
          <p className="truncate text-xs text-destructive">{testError ?? connection.last_error}</p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handleTest}
                disabled={testing}
                aria-label="Test connection"
              />
            }
          >
            <RefreshCw className={testing ? 'size-4 animate-spin' : 'size-4'} />
          </TooltipTrigger>
          <TooltipContent>Test connection</TooltipContent>
        </Tooltip>

        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" aria-label="Connection actions" />}>
            <MoreVertical className="size-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem variant="destructive" onClick={() => setConfirmingDelete(true)}>
              <Trash2 className="size-4" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <AlertDialog open={confirmingDelete} onOpenChange={setConfirmingDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this connection?</AlertDialogTitle>
            <AlertDialogDescription>
              "{connection.name}" will be removed for everyone. Any chat still using it will lose access to its
              tools.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
