# SSO setup (Entra ID / Google Workspace)

Every deployment gets email/password sign-in by default. Some customers need SSO instead — this repo's own company uses Entra ID, and at least one customer uses Google Workspace. SSO is Supabase Auth's built-in OAuth provider support, not code in this repo: Supabase acts as the OIDC relying party against the customer's identity provider and issues the same JWT shape regardless of how the user signed in, so the backend needs no changes (see `docs/architecture.md` → "SSO (Entra ID, Google Workspace)").

Each deployment is its own Supabase project with its own env config — there's no runtime "pick your tenant" step. Do these steps once per deployment that needs SSO.

## 1. Find this project's OAuth callback URL

Supabase Dashboard → **Authentication** → **URL Configuration**, or construct it directly:

```text
https://<project-ref>.supabase.co/auth/v1/callback
```

You'll register this exact URL as the redirect URI in the identity provider in both sections below.

## 2. Entra ID (Azure AD)

1. [Azure Portal](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations** → **New registration**.
2. Name it (e.g. `Document Copilot`), leave the default single-tenant/multi-tenant choice per your org's policy.
3. Under **Redirect URI**, add a **Web** platform entry with the callback URL from step 1.
4. After creation, note the **Application (client) ID** and **Directory (tenant) ID** from the app's Overview page.
5. **Certificates & secrets** → **New client secret** → note the secret value immediately (it's only shown once).
6. Supabase Dashboard → **Authentication** → **Providers** → **Azure** → enable it, paste the Client ID, Client Secret, and the tenant URL (`https://login.microsoftonline.com/<tenant-id>`).

## 3. Google Workspace

1. [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**.
2. Application type: **Web application**.
3. Under **Authorized redirect URIs**, add the callback URL from step 1.
4. If this is the workspace's first OAuth app, configure the **OAuth consent screen** first (internal or external, per the customer's Workspace policy).
5. Note the generated **Client ID** and **Client Secret**.
6. Supabase Dashboard → **Authentication** → **Providers** → **Google** → enable it, paste the Client ID and Client Secret.

## 4. Point the frontend at the enabled provider(s)

Set `VITE_SSO_PROVIDERS` in this deployment's frontend env to a comma-separated list matching what you enabled in Supabase (see `frontend/.env.example`):

```bash
# Entra ID only (this company's own deployment)
VITE_SSO_PROVIDERS=azure

# Google Workspace only (this customer's deployment)
VITE_SSO_PROVIDERS=google

# Both, or leave unset/empty for email/password only
VITE_SSO_PROVIDERS=azure,google
```

The sign-in page reads this once at build/boot time and renders the matching "Continue with Microsoft" / "Continue with Google" button(s) above the email/password form. An unrecognized value fails fast on startup instead of silently showing no button — a typo here needs to be caught, not swallowed.

## 5. Verify

1. Load the deployed frontend's sign-in page and confirm the expected SSO button(s) appear.
2. Click through and confirm the identity provider's consent/login screen appears, redirects back, and lands signed in.
3. Confirm `public.users` gets a row for the new identity (same upsert-on-first-request behavior as email/password — see `app/auth/dependencies.py`).

## Next steps

- [Supabase setup](supabase-setup.md) — the underlying Supabase project this SSO config attaches to
- [Frontend setup](frontend-setup.md) — where `VITE_SSO_PROVIDERS` and the rest of the frontend env live
