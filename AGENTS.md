# AGENTS

## Overview

This repository implements a real-time multiplayer drawing/guessing game.

- Frontend: Vue 3 + Pinia, built with Vite (folder: `frontend`).
- Backend: Python (FastAPI/uvicorn style) and small server logic (folder: `backend`).
- Tests: unit tests (Vitest for frontend, pytest for backend) and E2E (Playwright).

## Goals & Vision

Keep the project focused, simple, and maintainable:

- Keep code as simple as possible. Prefer clarity over cleverness.
- Keep functions small and responsibilities narrow.
- Minimize and prefer well-understood dependencies.

## Workflow Rules

- Run related unit tests after every set of changes.
- When writing new code, add tests for it before merging.
- Use project scripts and simple commands for linting, formatting, and testing.

Common command examples (run from the workspace root or the relevant subfolder):

```bash
# Backend (Python)
uv run pytest

# Frontend (Node)
npm install
npm run test:unit
npm run lint
npm run format
```

Notes

- Use `uv` for Python-related task runner commands and `npm` for Node tasks; prefer those over ad-hoc global tools in CI.
- Keep changes small and verified by tests. If a change touches both frontend and backend, run both test suites before pushing.
