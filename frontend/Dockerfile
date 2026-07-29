# syntax=docker/dockerfile:1

# --- Builder: pnpm install + vite build ---
FROM node:22-bookworm-slim AS builder

RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

COPY . .

# Vite bakes VITE_* vars into the static bundle at build time, so they must be
# supplied as build args (see docker-compose.yml), not left for runtime.
ARG VITE_API_BASE_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_SSO_PROVIDERS=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_SUPABASE_URL=${VITE_SUPABASE_URL} \
    VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY} \
    VITE_SSO_PROVIDERS=${VITE_SSO_PROVIDERS}

RUN pnpm build

# --- Runtime: static files behind nginx, no Node in production ---
FROM nginx:1.29-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
