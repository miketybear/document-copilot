# Build Checklist

Checklist theo trình tự đã định trong [architecture.md](architecture.md#implementation-sequence). Backend và frontend hiện chỉ có config rỗng (`pyproject.toml`, `.env.example`) — chưa có code thật, nên đây là toàn bộ đường đi từ số 0.

Quy tắc chung: mỗi phase là một **lát cắt dọc** (vertical slice) chạy được đầu-cuối trước khi qua phase tiếp theo, không viết hết backend rồi mới đụng frontend.

## Phase 0 — Môi trường & tài khoản

- [ ] Supabase project tạo xong (`docs/guides/supabase-setup.md`)
- [ ] Azure OpenAI resource + deployment cho chat model và embedding model
- [ ] `uv`, `pnpm`, Node 20+, Python 3.12+ cài local

## Phase 1 — Scaffold khung sườn (both)

- [x] `backend/app/main.py` — FastAPI entrypoint, health check route
- [x] `backend/app/config.py` — pydantic-settings, fail fast nếu thiếu env
- [x] `frontend` — Vite + React + TS strict, Tailwind, `shadcn` init, React Router
- [x] `frontend/src/lib/env.ts` — validate `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- [x] Smoke test: `GET /health` (backend) ↔ frontend Home page hiển thị "Backend: ok" trong browser

## Phase 2 — Data model (backend)

- [x] SQLAlchemy models: `users`, `chat_threads`, `chat_messages`, `message_citations`, `source_documents`, `document_chunks`
- [x] Alembic init, `env.py` trỏ vào metadata của models, dùng connection string session pooler (Direct connection IPv6-only, không route được trên mạng hiện tại)
- [x] Migration đầu tiên: `create extension vector`, các bảng trên, generated `tsvector`, HNSW + GIN index
- [x] Apply migration lên Supabase — đã drop schema cũ (leftover từ template SEC-filings gốc, 0 dòng dữ liệu) trước khi tạo schema mới
- [x] RLS bật trên cả 6 bảng + policy owner-scoped (chat data) / authenticated-read (document data)

## Phase 3 — Auth (both)

- [x] Frontend: Supabase email+password sign-in/sign-up qua `@supabase/supabase-js`, lưu session (`src/lib/auth.tsx`)
- [x] `backend/app/auth/dependencies.py` — verify `Authorization: Bearer` qua Supabase Auth (không tự verify JWT cục bộ), upsert `public.users`
- [x] Frontend: route bảo vệ (`RequireAuth`, redirect về `/sign-in` nếu chưa đăng nhập)
- [x] `GET /me` — endpoint test + hữu ích lâu dài, trả `{id, email}` của user đã xác thực
- [x] Test thủ công: sign up → `/me` trả đúng id/email → `public.users` được upsert đúng → sign out redirect về `/sign-in` → token thiếu/sai đều trả `401`

## Phase 4 — Chat plumbing, stub trước (both)

- [ ] `frontend/src/lib/http.ts` + `api.ts` — fetch wrapper, tự inject bearer token, typed `ApiError`
- [ ] Backend: endpoint tạo/list/get chat thread (chưa có LLM thật)
- [ ] Backend: `POST /chat/stream` — stub trả lời cố định, đúng format AI SDK stream
- [ ] Frontend: chat UI shell dùng `useChat` từ Vercel AI SDK, trỏ vào `/chat/stream`
- [ ] Chạy thử trong browser: gõ câu hỏi → thấy text stream về, dù nội dung là giả

## Phase 5 — Ingestion pipeline (backend)

- [ ] `ingest/` script: PDF/DOCX/PPT → Markdown chuẩn hóa
- [ ] Chunking theo heading, giữ `heading path`
- [ ] Gọi Azure OpenAI embedding deployment cho từng chunk
- [ ] Ghi `source_documents` + `document_chunks` vào Supabase (kèm `document_type`, `department`, `version`, `status`)

## Phase 6 — Retrieval (backend)

- [ ] Query `pgvector` semantic search trên `document_chunks.embedding`
- [ ] Query Postgres full-text search trên `search_vector`
- [ ] Reciprocal Rank Fusion (Python) gộp 2 danh sách
- [ ] `retrieval/retriever.py` expose bounded tools: `search_documents`, `read_chunk`, `read_surrounding_chunks`
- [ ] Unit test retrieval (không cần LLM)

## Phase 7 — LLM orchestration thật (backend)

- [ ] `assistant/agent.py`, `deps.py`, `outputs.py` (`GroundedAnswer`, `Citation`, `SourcePassage`), `instructions.md`
- [ ] `chat/orchestrator.py` — nối retrieval → agent → streaming → persist
- [ ] `grounding/validator.py` — enforce: mọi claim phải có citation, citation phải trỏ đúng passage đã retrieve
- [ ] Thay stub ở Phase 4 bằng response thật, test bằng câu hỏi thực tế với data đã ingest

## Phase 8 — UI hoàn thiện (frontend)

- [ ] Component hiển thị citation + source passage (company/tài liệu, section, excerpt)
- [ ] Empty state (không đủ evidence), streaming status, error state theo bảng lỗi trong architecture.md
- [ ] `pnpm tsc --noEmit` + `pnpm lint` sạch (nhớ: dự án này không viết frontend test)

## Phase 9 — Deploy on-prem

- [ ] Dockerfile backend, Dockerfile frontend (build tĩnh)
- [ ] `docker-compose.yml` + reverse proxy (Nginx/Caddy) route `/` → frontend, `/api` → backend
- [ ] Env thật cho Supabase + Azure OpenAI trên host on-prem, xác nhận outbound HTTPS tới 2 endpoint đó hoạt động
- [ ] Compose file + reverse-proxy config commit vào repo (secrets loại trừ)
