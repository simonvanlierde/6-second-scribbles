# spell-checker: ignore PYTHONUNBUFFERED, PYTHONDONTWRITEBYTECODE

# The Debian release is in the tag so a rebuild never moves to the next one by itself.
FROM python:3.14-slim-trixie AS runtime-base

# Create the non-root user for all runtime stages. USER names the numeric uid so a
# runtime (or Kubernetes runAsNonRoot) can tell it is not root without reading /etc/passwd.
# The upgrade takes Debian security fixes the base image has not been rebuilt with yet.
# Docker caches this layer, so it reruns only when the base image changes: deploy with
# `docker compose build --pull` so a new base image reaches it.
# pip is removed because uv installs everything and nothing calls pip at runtime; its
# vendored libraries were the only fixable HIGH findings in the image.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* && \
    rm -rf /usr/local/lib/python3.14/site-packages/pip /usr/local/lib/python3.14/site-packages/pip-*.dist-info /usr/local/bin/pip* && \
    groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid 1001 --create-home --home-dir /home/appuser --shell /bin/false appuser

ENV VIRTUAL_ENV=/opt/.venv \
    PATH="/opt/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

FROM runtime-base AS uv-base

# Tag plus digest: a tag alone can move. No bot updates this line, bump it by hand.
COPY --from=ghcr.io/astral-sh/uv:0.11.3@sha256:90bbb3c16635e9627f49eec6539f956d70746c409209041800a0280b93152823 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/.venv

# ── Dependency Layers ─────────────────────────────────────────────────────────
FROM uv-base AS deps-base

COPY pyproject.toml uv.lock ./

FROM deps-base AS dev-deps

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --group dev --no-install-project

FROM deps-base AS prod-deps

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM deps-base AS db-migrations-deps

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group db-migrations --no-install-project

FROM deps-base AS db-seed-deps

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group db-seed --no-install-project

# ── Source Layers ─────────────────────────────────────────────────────────────
FROM runtime-base AS app-source

COPY app ./app
# Read by app/__init__.py for the reported version.
COPY pyproject.toml ./

FROM app-source AS migrations-source

COPY alembic ./alembic
COPY alembic.ini ./

FROM app-source AS seed-source

COPY scripts/seed_data.py ./scripts/seed_data.py
COPY scripts/seed_data.yaml ./scripts/seed_data.yaml

# ── Dev ───────────────────────────────────────────────────────────────────────
FROM uv-base AS dev

COPY --from=dev-deps /opt/.venv /opt/.venv
COPY . .

ENV SERVER_HOST=0.0.0.0

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Prod ──────────────────────────────────────────────────────────────────────
FROM runtime-base AS prod

LABEL org.opencontainers.image.source="https://github.com/simonvanlierde/6-second-scribbles" \
      org.opencontainers.image.title="6 Second Scribbles backend" \
      org.opencontainers.image.description="FastAPI backend and WebSocket server for 6 Second Scribbles" \
      org.opencontainers.image.licenses="MIT"

COPY --chown=appuser:appuser --from=prod-deps /opt/.venv /opt/.venv
COPY --chown=appuser:appuser --from=app-source /app /app

USER 1001:1001

ENV SERVER_HOST=0.0.0.0

EXPOSE 8000

# No access log: Caddy already logs each request (with masked IPs), and uvicorn's
# would add the visitor's full forwarded IP.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]

# ── DB Ops ────────────────────────────────────────────────────────────────────
FROM runtime-base AS db-migrations

COPY --chown=appuser:appuser --from=db-migrations-deps /opt/.venv /opt/.venv
COPY --chown=appuser:appuser --from=migrations-source /app /app

USER 1001:1001

CMD ["alembic", "upgrade", "head"]

FROM runtime-base AS db-seed

COPY --chown=appuser:appuser --from=db-seed-deps /opt/.venv /opt/.venv
COPY --chown=appuser:appuser --from=seed-source /app /app

USER 1001:1001

CMD ["python", "scripts/seed_data.py"]
