# syntax=docker/dockerfile:1
# spell-checker: ignore healthchecks, PYTHONUNBUFFERED, PYTHONDONTWRITEBYTECODE

FROM python:3.14-slim AS runtime-base

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/.venv \
    PATH="/opt/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

FROM runtime-base AS uv-base

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/.venv

# ── Dev ───────────────────────────────────────────────────────────────────────
FROM uv-base AS dev

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-groups --no-install-project

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-groups

ENV SERVER_HOST=0.0.0.0

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Dependency Layers ─────────────────────────────────────────────────────────
FROM uv-base AS prod-deps

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM uv-base AS db-ops-deps

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group migrations --no-install-project

# ── Prod ──────────────────────────────────────────────────────────────────────
FROM uv-base AS prod-builder

COPY --from=prod-deps /opt/.venv /opt/.venv
COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM runtime-base AS prod

COPY --from=prod-builder /opt/.venv /opt/.venv
COPY . .

RUN useradd --create-home --home-dir /home/appuser --shell /bin/false appuser && \
    chown -R appuser:appuser /app /opt/.venv

USER appuser

ENV SERVER_HOST=0.0.0.0

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ── DB Ops ────────────────────────────────────────────────────────────────────
FROM uv-base AS db-ops-builder

COPY --from=db-ops-deps /opt/.venv /opt/.venv
COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group migrations

FROM runtime-base AS db-ops

COPY --from=db-ops-builder /opt/.venv /opt/.venv
COPY . .

RUN useradd --create-home --home-dir /home/appuser --shell /bin/false appuser && \
    chown -R appuser:appuser /app /opt/.venv

USER appuser

CMD ["alembic", "upgrade", "head"]
