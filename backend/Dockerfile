# syntax=docker/dockerfile:1

# ── Base ──────────────────────────────────────────────────────────────────────
FROM python:3.14-slim AS base

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    # copy instead of hardlinks — required when src and dst are on different filesystems (Docker layers)
    UV_LINK_MODE=copy \
    # install venv outside /app so dev volume mounts don't shadow it
    UV_PROJECT_ENVIRONMENT=/opt/.venv \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ── Dev ───────────────────────────────────────────────────────────────────────
FROM base AS dev

# Pre-install all deps (including dev) for layer caching — project itself excluded
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --all-groups --no-install-project

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-groups

ENV SERVER_HOST=0.0.0.0

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Prod ──────────────────────────────────────────────────────────────────────
FROM base AS prod

# Pre-install prod deps only for layer caching — project itself excluded
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Drop to a non-root user for security
RUN useradd --no-create-home --shell /bin/false appuser && \
    chown -R appuser:appuser /app /opt/.venv
USER appuser

ENV SERVER_HOST=0.0.0.0

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ── Migrations ────────────────────────────────────────────────────────────────
# Runs `alembic upgrade head` and exits. Used as a one-shot compose service.
FROM prod AS migrations

CMD ["uv", "run", "alembic", "upgrade", "head"]
