import { useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { describeApiError } from '@/lib/chatErrors'

type AuthType = 'api_token' | 'oauth2'

export function AddConnectionDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: () => void
}) {
  const [authType, setAuthType] = useState<AuthType>('api_token')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function reset() {
    setAuthType('api_token')
    setSubmitting(false)
    setError(null)
  }

  function handleOpenChange(next: boolean) {
    if (!next) reset()
    onOpenChange(next)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    const formData = new FormData(event.currentTarget)
    const name = formData.get('name') as string
    const serverUrl = formData.get('server_url') as string

    try {
      if (authType === 'api_token') {
        const apiToken = formData.get('api_token') as string
        await api.mcp.createApiTokenConnection(name, serverUrl, apiToken)
        onCreated()
        handleOpenChange(false)
      } else {
        // Leaves the SPA entirely to complete consent at the authorization server, so there's
        // nothing more to do here on success — the backend's callback redirects back to this
        // page when it's done.
        const { authorize_url } = await api.mcp.startOAuthConnection(name, serverUrl)
        window.location.href = authorize_url
      }
    } catch (err) {
      setError(describeApiError(err))
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add MCP connection</DialogTitle>
          <DialogDescription>
            Shared with everyone — connect once and the assistant can use it in any chat.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="name">Name</Label>
            <Input id="name" name="name" placeholder="Maximo" required />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="server_url">Server URL</Label>
            <Input
              id="server_url"
              name="server_url"
              type="url"
              placeholder="https://mcp.example.com/mcp"
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Authentication</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={authType === 'api_token' ? 'default' : 'outline'}
                className="flex-1"
                onClick={() => setAuthType('api_token')}
              >
                API token
              </Button>
              <Button
                type="button"
                variant={authType === 'oauth2' ? 'default' : 'outline'}
                className="flex-1"
                onClick={() => setAuthType('oauth2')}
              >
                OAuth 2.x
              </Button>
            </div>
          </div>

          {authType === 'api_token' ? (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="api_token">API token</Label>
              <Input id="api_token" name="api_token" type="password" required autoComplete="off" />
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              You'll be redirected to sign in and authorize access — no client ID or secret needed.
            </p>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {authType === 'api_token' ? 'Add connection' : 'Continue to authorize'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
