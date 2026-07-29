# Deploy runbook (Docker Compose)

Step-by-step CLI guide for standing up Document Copilot with the root [`docker-compose.yml`](../../docker-compose.yml). See [Deployment Shape](../architecture.md#deployment-shape) for the design this implements: a static frontend container, a stateless FastAPI backend container, and a reverse-proxy container (Caddy) that terminates TLS and routes `/` and `/api`.

## What runs where

| Container | Image | Purpose |
|---|---|---|
| `backend` | built from `backend/Dockerfile` | FastAPI + Uvicorn, port 8000 (not published to the host) |
| `frontend` | built from `frontend/Dockerfile` | static Vite build served by nginx, port 80 (not published to the host) |
| `reverse-proxy` | `caddy:2-alpine` | terminates TLS, publishes 80/443, routes `/api/*` → backend, everything else → frontend |

Supabase (auth + Postgres) and Azure OpenAI stay external, hosted services — nothing about them changes for this deploy. Both `backend` and `frontend` need outbound HTTPS to reach them; only `reverse-proxy`'s ports need to be reachable from employees' browsers.

## 1. Prerequisites on the host

- Docker Engine + the Compose plugin (`docker compose version` should print v2.x)
- Outbound HTTPS access to: your Supabase project, your Azure OpenAI endpoint, and `huggingface.co` / `*.hf.co` (the ingestion pipeline's `docling`/`rapidocr` models download from there on first use — see [ingest-runbook.md](ingest-runbook.md#model-downloads))
- A hostname for the app, if you want Caddy to provision a real TLS cert (see step 4)

## 2. Get the code and configure environment

```bash
git clone <your-repo-url> document-copilot
cd document-copilot
```

Three separate env files exist because they're read at different times by different processes — keep this straight or the deploy will look fine and then fail confusingly:

| File | Read by | When |
|---|---|---|
| `backend/.env` | `backend`'s FastAPI process | container start (`env_file:` in compose) |
| `frontend/.env` | you, as the source of truth for the values below | never read by Docker directly |
| `.env` (repo root) | `docker compose` itself | build time, to fill in `docker-compose.yml`'s `${...}` placeholders |

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env   # reference only — see below
cp .env.example .env
```

Fill in `backend/.env` with real Supabase + Azure OpenAI credentials (see [supabase-setup.md](supabase-setup.md) if you haven't provisioned Supabase yet).

Fill in the root `.env`:

- `DOMAIN` — the hostname employees will hit (or `:80` if a company-managed edge already terminates TLS in front of this host — see step 4).
- `VITE_API_BASE_URL` — `https://<DOMAIN>/api` (the frontend calls this at runtime; it's baked into the JS bundle at *build* time, which is why it's a build arg, not a container env var).
- `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` — same values as `frontend/.env`. The anon key is the public/browser-safe Supabase key, not the service role key — safe to bake into a static bundle.
- `VITE_SSO_PROVIDERS` — same as `frontend/.env`, e.g. `azure,google` or empty. See [sso-setup.md](sso-setup.md).

Keep `frontend/.env` in sync with the root `.env`'s `VITE_*` values — it exists for local `pnpm dev` and as the documented source of truth (per [`frontend/CLAUDE.md`](../../frontend/CLAUDE.md)), but Compose's build-arg interpolation only reads the root `.env`, not `frontend/.env`.

## 3. Build and start

```bash
docker compose build
docker compose up -d
```

First build pulls the Python/Node base images and resolves ~200 backend packages (docling's CPU-only torch build, not the CUDA one — see the comment in `backend/pyproject.toml` if you're curious why that matters) — expect several minutes on a cold cache. Subsequent builds are much faster.

## 4. Point Supabase at this domain

Easy to miss because nothing fails until someone actually signs in: Supabase Auth redirects the browser back to a URL it controls independently of anything in this repo's env files. **Supabase Dashboard → Authentication → URL Configuration**:

- **Site URL** — set to `https://<DOMAIN>` (or `http://<DOMAIN>` if you set `DOMAIN=:80`). This is Supabase's fallback redirect target, and it ships defaulted to `http://localhost:3000` on a new project — if you never touch it, that's where users land.
- **Redirect URLs** — add `https://<DOMAIN>/**` (matching your actual scheme) to the allow-list. The frontend explicitly requests `redirectTo: window.location.origin` on every sign-in (`src/pages/auth/SignIn.tsx`), but Supabase silently ignores that request and falls back to the Site URL above if the requested URL isn't allow-listed here — so both settings need to match this deployment, not just one of them.

Symptom if you skip this: SSO (or email/password) sign-in completes against Supabase/the identity provider successfully, then the browser gets redirected to whatever stale URL is in Site URL (often `http://localhost:3000`) and fails with `ERR_CONNECTION_REFUSED` — nothing wrong with the containers, just a dashboard setting that didn't move when the app did.

Update this every time `DOMAIN` changes (moving from local testing to a real on-prem hostname, for instance) — it's Supabase project config, not something `docker compose` can set for you.

## 5. TLS behavior (Caddy)

`reverse-proxy/Caddyfile` uses `{$DOMAIN}` as its site address, so:

- **Real DNS name reachable from the internet** (e.g. `copilot.yourcompany.com`) → Caddy automatically requests and renews a Let's Encrypt certificate. No extra config.
- **Internal-only name or `localhost`** → Caddy issues a cert from its own internal CA. Browsers will warn until that CA is trusted on client machines; fine for testing, usually not what you want for a company-wide rollout.
- **`:80`** → plain HTTP, no TLS. Use this when a company-managed reverse proxy/load balancer in front of this host already terminates TLS (common in on-prem setups where this Docker host sits behind an existing edge).

## 6. Verify

```bash
docker compose ps
docker compose logs -f backend
```

The backend's `/health` route isn't proxied by Caddy (only `/api/*` is — see [`reverse-proxy/Caddyfile`](../../reverse-proxy/Caddyfile)), so check it from inside the Docker network:

```bash
docker compose exec backend curl -sf http://localhost:8000/health
```

Then open `https://<DOMAIN>/` (or `http://<DOMAIN>/` if you set `DOMAIN=:80`) in a browser: sign-in page should load, and after signing in (including SSO, if step 4 is done), chat should stream answers with citations.

## 7. Redeploy after a code change

Containers are stateless — all durable data lives in Supabase — so redeploying is just rebuild + restart:

```bash
git pull
docker compose build
docker compose up -d
```

If only `backend/.env` or the root `.env` changed (no code changes), `docker compose up -d` alone picks up the new values — no rebuild needed for backend env changes, but frontend env changes (`VITE_*`) require a rebuild since they're baked into the static bundle:

```bash
docker compose build --no-cache frontend
docker compose up -d frontend
```

**Use `--no-cache` specifically when only `VITE_*` values changed and the source code didn't** — observed firsthand standing this up: BuildKit can reuse a cached `RUN pnpm build` layer from an earlier build even though the build-arg values differ, silently shipping the *old* `VITE_API_BASE_URL`/etc. baked into the bundle. Verify by grepping the served bundle for the expected value if in doubt:

```bash
docker compose exec frontend grep -o 'VITE_API_BASE_URL:`[^`]*`' /usr/share/nginx/html/assets/*.js
```

## 8. Logs and troubleshooting

```bash
docker compose logs -f              # all services
docker compose logs -f reverse-proxy  # Caddy — TLS issuance failures show up here
```

Common issues:

- **Caddy stuck retrying a cert** — usually `DOMAIN` isn't publicly resolvable to this host, or port 80/443 isn't reachable from the internet (needed for the Let's Encrypt HTTP-01 challenge). Switch to `:80` and let an upstream proxy handle TLS, or fix DNS/firewall.
- **Frontend loads but API calls fail with a network error** — check `VITE_API_BASE_URL` matches `DOMAIN` exactly (including `https://` vs `http://`), and that you rebuilt the frontend image after changing it.
- **Backend container exits immediately** — almost always a missing/invalid var in `backend/.env`; `app/config.py` fails fast on startup, so `docker compose logs backend` will name the missing field directly.
- **Sign-in succeeds against the identity provider, then `ERR_CONNECTION_REFUSED` on redirect** — Supabase's Site URL/Redirect URLs weren't updated for this `DOMAIN`; see step 4.

## Can this run anywhere Docker runs, not just on-prem?

Technically yes — nothing in these containers is on-prem-specific. They only need outbound HTTPS to Supabase and Azure OpenAI, and don't call any on-prem-only API, so the same images run unchanged on a cloud VM, a managed container service, or any other Docker host. That said, [`CLAUDE.md`](../../CLAUDE.md) currently locks the documented hosting decision to on-premise Docker Compose — if you actually want to move hosting to cloud infrastructure, treat that as a deliberate stack change (update `CLAUDE.md`'s `Hosting` line and `docs/architecture.md`'s Deployment Shape) rather than an incidental side effect of "it happens to work."
