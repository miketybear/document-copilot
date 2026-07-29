# Ingestion pipeline runbook

Step-by-step CLI guide for adding, updating, or re-ingesting documents into the corpus. The pipeline is a one-off script (`backend/ingest/run.py`), not part of the request-serving path — run it whenever the document set changes, not on every deploy.

## Pipeline stages

`ingest/run.py` orchestrates four steps per manifest entry, all in [`backend/ingest/`](../../backend/ingest/) + [`app/embeddings.py`](../../backend/app/embeddings.py):

1. **Convert** (`convert.py`) — PDF/DOCX/PPTX → Markdown via `docling`, with automatic OCR for scanned PDFs (no config needed; docling detects pages without a text layer).
2. **Chunk** (`chunk.py`) — splits Markdown along heading/paragraph boundaries, max 500 tokens per chunk (`tiktoken`, `cl100k_base`), each chunk keeps its ancestor heading titles (`heading_path`).
3. **Embed** (`app/embeddings.py`) — calls the Azure OpenAI embedding deployment for every chunk.
4. **Load** (`load.py`) — writes one `source_documents` row + N `document_chunks` rows via the Supabase service-role client.

## Adding or updating a document

1. Drop the file into `data/` (raw files are gitignored — see the repo's `.gitignore`).
2. Add (or edit) its entry in `data/manifest.json`:

   ```json
   {
     "file": "your-file.pdf",
     "title": "Human-readable document title",
     "document_type": "policy",
     "department": "Human Resources",
     "owner": "Company Name",
     "version": "1.0",
     "effective_date": "2026-01-15"
   }
   ```

   `file`, `title`, and `document_type` are required. `department`, `owner`, `version` are optional (`null`/omit if unknown). `effective_date` is `null` or an ISO date string.

3. **Supersede semantics**: `upsert_document` (`load.py:18`) matches on exact `title` string against the current `source_documents` row. Re-running the manifest with the *same* title creates a new row and flips the old one to `status=superseded` — it does not update in place, and it does not match on filename. Rename the title deliberately if you want a new document lineage instead of a new version of an existing one.

## Running locally

```bash
cd backend
uv sync
uv run python -m ingest.run --manifest ../data/manifest.json
```

`--manifest` defaults to `../data/manifest.json` (relative to `backend/`), so if you're ingesting the default corpus you can drop the flag. Requires `backend/.env` to have real Supabase + Azure OpenAI credentials — this talks to both live services, there's no dry-run mode.

Expected output per document:

```text
Converting your-file.pdf...
  42 chunks, embedding...
  done: document_id=<uuid>
```

## Running via Docker (on-prem host, no local `uv`)

The `backend` image already contains `ingest/` and its dependencies (docling is a main dependency, not dev-only), so no separate ingest image is needed:

```bash
docker compose run --rm backend uv run python -m ingest.run --manifest ../data/manifest.json
```

`--rm` matters here — this is a one-off job, not a long-lived service; without it you'd accumulate stopped containers. `docker compose run` uses the same `backend/.env` as the running service (via `env_file:` in `docker-compose.yml`), so no extra config is needed as long as `docker compose up -d` has already been configured per [deploy-onprem.md](deploy-onprem.md).

## Model downloads

The first `docling`/`rapidocr` conversion on a fresh environment downloads layout and OCR models from Hugging Face (a few hundred MB) — this needs outbound HTTPS to `huggingface.co`/`*.hf.co`, in addition to Supabase and Azure OpenAI. `docker-compose.yml` mounts a `backend_cache` volume at `/app/.cache` specifically so this only happens once per host, not on every `docker compose run`. If ingestion hangs on the first `Converting ...` line for a while with no network issue, that's expected — it's downloading models, not stuck.

## Verifying results

In the Supabase dashboard (Table Editor) or via SQL:

```sql
select id, title, status, effective_date
from source_documents
order by created_at desc;

select count(*) from document_chunks where document_id = '<uuid from above>';
```

Confirm: the row's `status` is `current` (and, if this was a re-ingest, the previous version flipped to `superseded`), the chunk count is non-trivial, and `document_chunks.chunk_text` reads correctly for a spot-checked row — OCR'd scans in particular are worth eyeballing once.

## Troubleshooting

- **Azure OpenAI errors on the embed step** — `AZURE_OPENAI_ENDPOINT` must be the bare resource root (e.g. `https://your-resource.cognitiveservices.azure.com`), no `/openai/v1` or `/api/projects/...` suffix; the SDK builds the full path itself. Verify `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` matches the exact deployment name in Azure AI Foundry (not the underlying model name) and `AZURE_OPENAI_API_VERSION` is a version your resource actually supports.
- **`AZURE_OPENAI_EMBEDDING_DIMENSIONS` mismatch** — must match what the embedding deployment actually returns, or inserts into `document_chunks.embedding` (a fixed-width `vector` column) fail.
- **Garbled characters in `chunk_text` for OCR'd scans** — known open issue: docling's Markdown output for some scanned PDFs contains undecoded HTML entities (`&gt;`, `&amp;`). Not fixed by this pipeline yet; check before trusting an OCR'd document's chunk text verbatim in citations.
- **Re-ingest didn't create a new version** — check the `title` in `data/manifest.json` matches the existing row's `title` *exactly* (see Supersede semantics above); a typo'd title creates an unrelated new document instead of superseding.
