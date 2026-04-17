# 6 Second Scribbles

Real-time multiplayer drawing and guessing built for quick room-based play.

This repo contains a Vue 3 frontend, a FastAPI backend, and tracked contract artifacts that keep the two sides in sync.

## Quick Start

Prerequisites:

- Node.js 24+
- Python 3.14+
- Docker
- `just`

Common repo-level commands:

```bash
just install
just dev
just up
just up-prod
just test
just check
just generate-contracts
```

## Docs

- [Frontend](frontend/README.md)
- [Backend](backend/README.md)
- [Contracts](contracts/README.md)

## About

The game assigns a category and a short list of prompts each round. Players draw as many prompts as they can, then the room moves through guessing, round results, and final results.

The implementation is intentionally simple and early-stage, so code and behavior may change when that makes the system easier to understand and maintain.

## Attribution

This multiplayer implementation is inspired by:

1. The original physical game, *Six Second Scribbles*, created by Hazel Reynolds and published by [Gamely Games](https://gamelygames.com/products/six-second-scribbles).
2. The original solo web version by Oliver Culley de Lange, available on [GitHub](https://github.com/OliverCulleyDeLange/6ss).

## License

The code for this multiplayer implementation is released under the MIT License.
The *Six Second Scribbles* game concept, brand, and original card content remain the property of their respective owners.
