FROM node:26-trixie-slim AS base

ENV PNPM_HOME=/pnpm \
    PATH="/pnpm:$PATH"

# Node 25+ no longer bundles Corepack, so it has to be installed before it can be
# enabled. Corepack is kept rather than installing pnpm directly so that
# package.json's `packageManager` field stays the one source of the pnpm version.
RUN npm install -g corepack@latest && corepack enable

WORKDIR /app

FROM base AS deps

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/package.json

RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm fetch --frozen-lockfile --filter ./frontend... && \
    pnpm install --frozen-lockfile --offline --ignore-scripts --filter ./frontend...

FROM deps AS dev

COPY frontend frontend

WORKDIR /app/frontend

EXPOSE 3001

CMD ["pnpm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3001"]

FROM deps AS build

COPY frontend frontend

WORKDIR /app/frontend

RUN pnpm run build

FROM caddy:2.11-alpine AS prod

LABEL org.opencontainers.image.source="https://github.com/simonvanlierde/6-second-scribbles" \
      org.opencontainers.image.title="6 Second Scribbles frontend" \
      org.opencontainers.image.description="Caddy serving the 6 Second Scribbles web app and proxying /api to the backend" \
      org.opencontainers.image.licenses="MIT"

# Takes Alpine security fixes the base image has not been rebuilt with yet. Docker
# caches this layer: build with --pull so a new base image reaches it.
RUN apk upgrade --no-cache

COPY frontend/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/frontend/dist /usr/share/caddy

EXPOSE 80
