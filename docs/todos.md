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

- [x] `frontend/src/lib/http.ts` + `api.ts` — fetch wrapper, tự inject bearer token, typed `ApiError`
- [x] Backend: `database/chats.py` dùng user-scoped Supabase client (JWT của user) + RLS đã bật ở Phase 2, không dùng service-role cho chat data
- [x] Backend: `POST/GET /chat/threads`, `GET /chat/threads/{id}` — tạo/list/get thread (chưa có LLM thật)
- [x] Backend: `POST /chat/stream` — stub trả lời cố định, đúng UI Message Stream Protocol (verify trực tiếp từ package `ai` đã cài, không đoán)
- [x] Frontend: chat UI (`ChatPage`, `ChatConversation`, `ChatMessageList`, `ChatInput`) dùng `useChat` từ `@ai-sdk/react`, trỏ vào `/chat/stream`; thay route `/` từ Home smoke-test cũ
- [x] Test trong browser: gõ câu hỏi → text stream về đúng → refresh/mở lại thread → lịch sử load đúng → thread không tồn tại/không phải của mình → hiện lỗi rõ ràng (không treo trắng trang)
- [x] Fix 2 bug phát hiện khi test: `NewChat` tạo trùng 2 thread do StrictMode double-effect (thiếu guard); `ChatPage` treo vô hạn ở "Loading…" khi `getThread` lỗi (thiếu `.catch`)

## Phase 5 — Ingestion pipeline (backend)

- [x] `ingest/convert.py` — PDF/DOCX/PPT → Markdown chuẩn hóa qua **docling** (OCR tự động cho PDF scan, đã verify thật với 1 file scan)
- [x] `ingest/chunk.py` — chunking theo heading (`heading_path`), đếm token bằng `tiktoken`
- [x] `ingest/embed.py` — gọi Azure OpenAI embedding deployment (`AzureOpenAI` client, endpoint dạng `*.cognitiveservices.azure.com`, truyền `dimensions` tường minh để khớp schema)
- [x] `ingest/load.py` — ghi `source_documents` + `document_chunks` qua service-role client; logic supersede (version mới → row cũ chuyển `status=superseded` + `superseded_by`) đã test riêng
- [x] `data/manifest.json` + `ingest/run.py` — CLI orchestrator, chạy thật trên 3 tài liệu thật (2 demo HR policy EN/VN + 1 Work Instruction thật của BDPOC dạng scan)
- [x] Verify trong Supabase: 3 `source_documents` (đủ metadata), 291 `document_chunks` (embedding + search_vector đầy đủ), OCR đọc đúng nội dung kỹ thuật từ file scan
- [x] Debug thật với Azure AI Foundry: sửa endpoint sai (dư path `/responses`, dư `/api/projects/...`), sai tên deployment (`-small` vs `-large`), `api_version` không hợp lệ — cuối cùng chốt `AzureOpenAI` client + endpoint `*.cognitiveservices.azure.com` (bare root) + `api_version=2024-10-21`

## Phase 6 — Retrieval (backend)

- [x] Migration mới: 2 Postgres RPC function `search_chunks_semantic`/`search_chunks_fulltext` (`SECURITY INVOKER`, giữ nguyên RLS)
- [x] `app/embeddings.py` — tách logic embedding dùng chung cho `ingest/` và `retrieval/` (ingest phụ thuộc app, không ngược lại)
- [x] `app/retrieval/queries.py` — gọi 2 RPC qua user-scoped Supabase client
- [x] `app/retrieval/fusion.py` — Reciprocal Rank Fusion thuần Python
- [x] `app/retrieval/retriever.py` — 3 bounded tools: `search_documents`, `read_chunk`, `read_surrounding_chunks`; type `SourcePassage`
- [x] Thêm `pytest`/`pytest-asyncio`; 12 test (4 unit fusion, 5 mocked retriever, 3 integration thật) — tất cả pass
- [x] Verify thật: search "safety level transmitter" trả đúng chunk từ đúng tài liệu Work Instruction
- [x] Fix bug test isolation: cache client Supabase ở module-level (đúng cho production) xung đột với event loop riêng của mỗi test → thêm fixture reset cache trong `conftest.py`

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
