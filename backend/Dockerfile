# syntax=docker/dockerfile:1

# --- Builder: resolve + install deps with uv, using the lockfile as-is ---
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install deps first (cached layer, invalidated only by lockfile changes), then add source.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# --- Runtime: slim image, no uv/build toolchain ---
FROM python:3.12-slim-bookworm

RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

# Non-root HOME so docling/rapidocr/huggingface_hub can write their model caches
# (see docker-compose.yml, which mounts a named volume at /app/.cache so those
# downloads survive container restarts instead of re-fetching on every ingest run).
ENV HOME=/app \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

RUN mkdir -p /app/.cache && chown app:app /app/.cache

USER app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
