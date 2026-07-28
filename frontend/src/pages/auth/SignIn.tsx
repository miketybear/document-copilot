import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { GoogleIcon, MicrosoftIcon } from '@/components/icons/SsoIcons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { env, type SsoProvider } from '@/lib/env'
import { supabase } from '@/lib/supabase'

type Mode = 'sign-in' | 'sign-up'

const SSO_LABELS: Record<SsoProvider, string> = {
  azure: 'Continue with Microsoft',
  google: 'Continue with Google',
}

const SSO_ICONS: Record<SsoProvider, typeof MicrosoftIcon> = {
  azure: MicrosoftIcon,
  google: GoogleIcon,
}

export function SignIn() {
  const [mode, setMode] = useState<Mode>('sign-in')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  async function handleSsoSignIn(provider: SsoProvider) {
    setError(null)
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: window.location.origin },
    })
    if (error) setError(error.message)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    const formData = new FormData(event.currentTarget)
    const email = formData.get('email') as string
    const password = formData.get('password') as string

    const { error } =
      mode === 'sign-in'
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password })

    setSubmitting(false)

    if (error) {
      setError(error.message)
      return
    }

    navigate('/')
  }

  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4">
      <div className="flex w-full max-w-sm flex-col gap-4">
        <h1 className="text-xl font-semibold text-foreground">
          {mode === 'sign-in' ? 'Sign in' : 'Sign up'}
        </h1>

        {env.ssoProviders.length > 0 && (
          <div className="flex flex-col gap-2">
            {env.ssoProviders.map((provider) => {
              const Icon = SSO_ICONS[provider]
              return (
                <Button
                  key={provider}
                  type="button"
                  variant="outline"
                  onClick={() => handleSsoSignIn(provider)}
                >
                  <Icon className="size-4" />
                  {SSO_LABELS[provider]}
                </Button>
              )
            })}

            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="h-px flex-1 bg-border" />
              or
              <span className="h-px flex-1 bg-border" />
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Email</Label>
            <Input id="email" name="email" type="email" required autoComplete="email" />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              required
              minLength={6}
              autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'}
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button type="submit" disabled={submitting}>
            {mode === 'sign-in' ? 'Sign in' : 'Sign up'}
          </Button>

          <button
            type="button"
            className="text-sm text-muted-foreground underline"
            onClick={() => setMode(mode === 'sign-in' ? 'sign-up' : 'sign-in')}
          >
            {mode === 'sign-in' ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
          </button>
        </form>
      </div>
    </main>
  )
}
