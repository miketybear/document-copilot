import { useEffect, useState } from 'react'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { api, type MCPConnection, type MCPTool } from '@/lib/api'
import { describeApiError } from '@/lib/chatErrors'

export function ToolsDialog({
  connection,
  open,
  onOpenChange,
}: {
  connection: MCPConnection
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [tools, setTools] = useState<MCPTool[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setTools(null)
    setError(null)
    api.mcp
      .listTools(connection.id)
      .then(setTools)
      .catch((err: unknown) => setError(describeApiError(err)))
  }, [open, connection.id])

  async function toggleTool(tool: MCPTool, enabled: boolean) {
    if (!tools) return
    const previous = tools
    const next = tools.map((t) => (t.name === tool.name ? { ...t, enabled } : t))
    setTools(next)
    setSaving(tool.name)
    try {
      await api.mcp.setDisabledTools(
        connection.id,
        next.filter((t) => !t.enabled).map((t) => t.name)
      )
    } catch (err) {
      setTools(previous)
      setError(describeApiError(err))
    } finally {
      setSaving(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Tools — {connection.name}</DialogTitle>
          <DialogDescription>
            Turn off tools you don't want the assistant to use from this connection.
          </DialogDescription>
        </DialogHeader>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {tools === null ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : tools.length === 0 ? (
          <p className="text-sm text-muted-foreground">This server doesn't expose any tools.</p>
        ) : (
          <div className="flex max-h-80 flex-col gap-3 overflow-y-auto">
            {tools.map((tool) => (
              <div key={tool.name} className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <Label htmlFor={`tool-${tool.name}`} className="font-mono text-sm">
                    {tool.name}
                  </Label>
                  {tool.description && (
                    <Tooltip>
                      <TooltipTrigger render={<p className="truncate text-xs text-muted-foreground" />}>
                        {tool.description}
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs text-pretty">{tool.description}</TooltipContent>
                    </Tooltip>
                  )}
                </div>
                <Switch
                  id={`tool-${tool.name}`}
                  checked={tool.enabled}
                  disabled={saving === tool.name}
                  onCheckedChange={(checked) => toggleTool(tool, checked)}
                />
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
