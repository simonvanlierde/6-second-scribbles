FROM node:24-bookworm-slim AS base

ENV PNPM_HOME=/pnpm \
    PATH="/pnpm:$PATH"

RUN corepack enable

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

FROM caddy:2.10-alpine AS prod

COPY frontend/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/frontend/dist /usr/share/caddy

EXPOSE 80
