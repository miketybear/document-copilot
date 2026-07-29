# SSO setup (Entra ID / Google Workspace)

Every deployment gets email/password sign-in by default. Some customers need SSO instead — this repo's own company uses Entra ID, and at least one customer uses Google Workspace. SSO is Supabase Auth's built-in OAuth provider support, not code in this repo: Supabase acts as the OIDC relying party against the customer's identity provider and issues the same JWT shape regardless of how the user signed in, so the backend needs no changes (see `docs/architecture.md` → "SSO (Entra ID, Google Workspace)").

Each deployment is its own Supabase project with its own env config — there's no runtime "pick your tenant" step. Do these steps once per deployment that needs SSO.

**The round trip, in order:** get this project's callback URL (already exists, nothing to create) → register it as the redirect URI *in the identity provider* (Azure Portal / Google Cloud Console — not in Supabase) → the identity provider hands you back a Client ID + Client Secret → paste *those* into the Supabase Dashboard. The callback URL flows out to the identity provider; the Client ID/Secret flow back into Supabase. Nothing about the callback URL itself is configured inside Supabase.

## 1. Get this project's OAuth callback URL

This URL isn't something you create or enable — every Supabase project already listens on it. You only need to fill in your own project ref:

```text
https://<project-ref>.supabase.co/auth/v1/callback
```

The project ref is the subdomain in your `VITE_SUPABASE_URL` / `SUPABASE_URL` (e.g. if that's `https://bhfbjhhyjloscyufmqiu.supabase.co`, your callback URL is `https://bhfbjhhyjloscyufmqiu.supabase.co/auth/v1/callback`). You can also read it off Supabase Dashboard → **Authentication** → **URL Configuration**, but it's the same value either way — there's no button to press there.

Copy this exact URL — you'll paste it into the identity provider (Entra ID or Google), not into Supabase, in the next two sections.

## 2. Entra ID (Azure AD)

Steps 1–3 happen in Azure, not Supabase:

1. [Azure Portal](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations** → **New registration**.
2. Name it (e.g. `Document Copilot`), leave the default single-tenant/multi-tenant choice per your org's policy.
3. Under **Redirect URI**, add a **Web** platform entry and paste the callback URL from step 1 above. This is the only place that URL gets entered.
4. After creation, note the **Application (client) ID** and **Directory (tenant) ID** from the app's Overview page.
5. **Token configuration** → **Add optional claim** → token type **ID** → check **email** → **Add**. If Azure prompts to also add the corresponding Microsoft Graph email permission, accept it. **Do this even if it seems redundant** — without it, sign-in completes (including MFA) but Supabase fails afterward with `Error getting user email from external provider`, because Entra ID doesn't include the email claim in the ID token by default.
6. **Certificates & secrets** → **New client secret** → note the secret value immediately (it's only shown once).
7. **Back in the Supabase Dashboard** → **Authentication** → **Providers** → **Azure** → enable it, paste the Client ID, Client Secret, and the tenant URL (`https://login.microsoftonline.com/<tenant-id>`) from steps 4 and 6. The callback URL itself is not re-entered here — Supabase already knows its own URL.

**If sign-in still redirects back with `error=server_error&error_code=unexpected_failure&error_description=Error+getting+user+email+from+external+provider`** after step 5: the signed-in Entra ID user's **Mail** attribute is likely empty (common for accounts without an Exchange Online mailbox, or ones only ever used with a bare User Principal Name). Microsoft Entra ID admin center → **Users** → the affected user → confirm **Mail** (not Username/UPN) is actually populated. Without a real mail attribute, Entra ID has no email to hand back regardless of the optional claim.

## 3. Google Workspace

Steps 1–3 happen in Google Cloud Console, not Supabase:

1. [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**.
2. Application type: **Web application**.
3. Under **Authorized redirect URIs**, add the callback URL from step 1 above. This is the only place that URL gets entered.
4. If this is the workspace's first OAuth app, configure the **OAuth consent screen** first (internal or external, per the customer's Workspace policy).
5. Note the generated **Client ID** and **Client Secret**.
6. **Back in the Supabase Dashboard** → **Authentication** → **Providers** → **Google** → enable it, paste the Client ID and Client Secret from step 5. The callback URL itself is not re-entered here.

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

**If step 2 completes at the identity provider but then the browser gets `ERR_CONNECTION_REFUSED`** on redirect: Supabase's own **Site URL** / **Redirect URLs** (Dashboard → Authentication → URL Configuration) haven't been updated to match wherever this deployment is actually served — a separate setting from the callback URL in section 1, and easy to forget when moving from local dev to a real deployment. See [deploy-onprem.md](deploy-onprem.md#4-point-supabase-at-this-domain).

## Next steps

- [Supabase setup](supabase-setup.md) — the underlying Supabase project this SSO config attaches to
- [Frontend setup](frontend-setup.md) — where `VITE_SSO_PROVIDERS` and the rest of the frontend env live
