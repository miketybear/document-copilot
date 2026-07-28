function requireEnv(key: string): string {
  const value = import.meta.env[key]
  if (!value) {
    throw new Error(`Missing required env var: ${key}`)
  }
  return value
}

export type SsoProvider = 'azure' | 'google'

const KNOWN_SSO_PROVIDERS: SsoProvider[] = ['azure', 'google']

function parseSsoProviders(key: string): SsoProvider[] {
  const raw = import.meta.env[key]
  if (!raw) return []

  return raw.split(',').map((entry) => {
    const provider = entry.trim()
    if (!KNOWN_SSO_PROVIDERS.includes(provider as SsoProvider)) {
      throw new Error(
        `Invalid ${key} value "${provider}" — must be one of: ${KNOWN_SSO_PROVIDERS.join(', ')}`,
      )
    }
    return provider as SsoProvider
  })
}

export const env = {
  apiBaseUrl: requireEnv('VITE_API_BASE_URL'),
  supabaseUrl: requireEnv('VITE_SUPABASE_URL'),
  supabaseAnonKey: requireEnv('VITE_SUPABASE_ANON_KEY'),
  // Which SSO buttons to show on the sign-in page for this deployment — empty means email/password
  // only. Each provider must already be configured in the Supabase project's Auth providers.
  ssoProviders: parseSsoProviders('VITE_SSO_PROVIDERS'),
}
