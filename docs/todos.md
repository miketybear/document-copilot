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

- [x] Thêm `pydantic-ai`; verify thật API (`Agent`, `@agent.tool`, `AzureProvider`) và endpoint chat model — hóa ra cùng cấu hình `AzureOpenAI` cổ điển đã verify cho embedding ở Phase 5 dùng được luôn cho chat, chỉ đổi tên deployment
- [x] `assistant/outputs.py` (`GroundedAnswer`, `Citation`), `deps.py` (`DocumentAgentDeps`), `instructions.md` (product contract: chỉ trả lời từ passage đã retrieve, cite mọi claim, nói rõ khi thiếu bằng chứng, không diễn giải ràng buộc, **citation chỉ ở field structured, không nhét thô vào câu trả lời**)
- [x] `assistant/agent.py` — đăng ký 3 tool Phase 6 làm agent tools
- [x] `grounding/validator.py` — enforce citation phải trỏ đúng chunk đã retrieve trong lượt chạy này
- [x] `chat/orchestrator.py` viết lại — chạy agent xong → validate → nếu pass thì giả lập stream + persist message + persist `message_citations`; nếu fail thì trả lỗi có kiểm soát, không stream câu trả lời chưa validate
- [x] Thêm INSERT policy còn thiếu cho `message_citations` (Phase 2 chỉ có SELECT)
- [x] Test: 4 unit validator, 3 mocked orchestrator (bao gồm case citation "bịa" phải bị chặn), 2 integration thật (câu hỏi thật + câu hỏi ngoài phạm vi corpus) — tất cả pass
- [x] Test thủ công qua UI thật: 2 câu hỏi thật ("safety level transmitter maintenance", "maternity leave policy") → trả lời đúng, citation đúng tài liệu, verify trong `message_citations`
- [x] Fix bug thật: agent tự "nhớ nhầm" chunk_id (UUID sai) khi gọi tool → Postgres lỗi crash cả request → thêm validate UUID ở boundary trong `retriever.py` trước khi query

## Phase 8 — UI hoàn thiện (frontend)

- [x] Component hiển thị citation + source passage (company/tài liệu, section, excerpt) — `Citation.tsx`, excerpt rút gọn + "Show more"
- [x] Backend: stream + persist citation làm structured `data-citation` UI message part (trước đó Phase 7 mới ghi vào `message_citations`, không đẩy metadata ra client) — `chat/streaming.py`, `chat/messages.py`, `chat/orchestrator.py`
- [x] Backend: fix rò rỉ exception nội bộ ra `errorText` gửi cho client — log qua `structlog`, chỉ stream message cố định thân thiện
- [x] Empty state (không đủ evidence), streaming status ("Searching documents…" / "Answering…"), error state (404/401/network/grounding-failure) theo bảng lỗi trong architecture.md — `chatErrors.ts`
- [x] `pnpm tsc --noEmit` + `pnpm lint` sạch (nhớ: dự án này không viết frontend test)
- [x] Test thủ công qua UI thật: câu hỏi có evidence (6 citation đúng tài liệu, excerpt expand/collapse) → câu hỏi ngoài phạm vi (empty state) → reload page (citation persist đúng) → thread không tồn tại (404 friendly) → tắt backend giữa chừng (network error friendly, console giữ raw error) → backend sống lại, gửi tiếp bình thường
- [x] Bug phát hiện khi test (ngoài phạm vi Phase 8, đã tách task riêng): `chunk_text` của tài liệu scan chứa HTML entity chưa decode (`&gt;`, `&amp;`) — lỗi ở ingestion pipeline Phase 5, không phải UI
- [x] Loạt cải tiến UI/UX theo yêu cầu sau khi Phase 8 xong: redesign theme (teal/slate palette, Geist Mono cho metadata), app shell với sidebar (danh sách thread theo Pinned/Today/Earlier, pin/delete có confirm dialog, dark mode toggle theo OS + lưu localStorage, scrollbar CSS thuần), auto-derive thread title từ câu hỏi đầu (`derive_title`), ẩn thread chưa có title khỏi sidebar tới khi lượt đầu xong, landing page mới cho "New chat" (greeting + input giữa màn hình, chỉ tạo thread khi gửi tin nhắn đầu — giống ChatGPT/Claude), render markdown thật cho câu trả lời (`react-markdown`, bullet/numbered list đúng thay vì dồn 1 đoạn)
- [x] Bug phát hiện thêm, đã tách task riêng: model đôi khi in literal `[citation]` trong câu trả lời — vi phạm chính `instructions.md` (citation chỉ nên ở structured field)

## Bổ sung — SSO (Entra ID / Google Workspace)

Yêu cầu thật: công ty tự dùng Entra ID, 1 khách hàng dùng Google Workspace. Backend giữ nguyên `cloud Supabase` (chưa switch on-prem).

- [x] Xác nhận `app/auth/dependencies.py` không cần đổi gì — Supabase Auth phát JWT cùng 1 dạng dù đăng nhập bằng email/password hay SSO, nên vẫn verify được qua đúng 1 đường
- [x] Không thêm abstraction `AuthVerifier` — mọi provider hiện có (email, Entra ID, Google) đều đi qua cùng 1 code path; chỉ tách interface khi có khách hàng cần nguồn định danh Supabase Auth không broker được (vd gateway tự SSO rồi forward header) — lúc đó mới là lời gọi thứ 2 thật, không phải giả định
- [x] Frontend: `env.ts` thêm `VITE_SSO_PROVIDERS` (danh sách provider cho phép, fail-fast nếu giá trị lạ), `SignIn.tsx` hiện nút "Continue with Microsoft"/"Continue with Google" phía trên form email/password khi được cấu hình — dùng thẳng `supabase.auth.signInWithOAuth()`, không cần route callback riêng (`detectSessionInUrl` mặc định của `@supabase/supabase-js` tự xử lý)
- [x] Test: không cấu hình → giữ nguyên UI cũ (email/password only); cấu hình `azure,google` → hiện đúng 2 nút; giá trị provider sai → app fail-fast thay vì âm thầm bỏ qua
- [x] Cập nhật tài liệu: `frontend/CLAUDE.md`, `docs/architecture.md` (thêm mục "SSO (Entra ID, Google Workspace)"), `docs/guides/supabase-setup.md`, `docs/guides/sso-setup.md` (mới — hướng dẫn đăng ký app trên Entra ID/Google Cloud Console + bật provider trên Supabase Dashboard, các bước này ngoài phạm vi code, phải làm tay)
- [x] Test thật với Entra ID (tài khoản công ty `biendongpoc.vn`), qua Edge, MFA Authenticator thật: bấm "Continue with Microsoft" → Seamless SSO tự nhận tài khoản Windows → approve MFA → đăng nhập thành công vào app
- [x] Bug thật gặp phải khi test: redirect về app không lỗi hiển thị nhưng không có session — do Entra ID không trả `email` claim mặc định, Supabase báo `Error getting user email from external provider` (thấy qua Network tab, response header `location` của request `token?grant_type=pkce`). Fix: Azure Portal → App registration → Token configuration → Add optional claim → ID token → `email`. Đã ghi lại thành bước bắt buộc + troubleshooting note trong `docs/guides/sso-setup.md`

## Phase 9 — Deploy on-prem

- [ ] Dockerfile backend, Dockerfile frontend (build tĩnh)
- [ ] `docker-compose.yml` + reverse proxy (Nginx/Caddy) route `/` → frontend, `/api` → backend
- [ ] Env thật cho Supabase + Azure OpenAI trên host on-prem, xác nhận outbound HTTPS tới 2 endpoint đó hoạt động
- [ ] Compose file + reverse-proxy config commit vào repo (secrets loại trừ)
