# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-07-06

### Added

- Accessibility checks in CI.
- Architecture, contributing, ADR, and changelog documentation.
- Late-joiner hydration for shared lobby doodles.

### Changed

- Hardened multiplayer room lifecycle, host migration, kick votes, timers, and WebSocket room-creation throttling.
- Improved guess scoring for non-Latin text, short fuzzy matches, duplicate guesses, and localized cache keys.
- Optimized shared drawpad sync by sending stroke deltas instead of full growing strokes.
- Simplified frontend game/drawing state and refreshed invite, lobby, settings, and spectator flows.
- Updated project tooling to Node 26 and pnpm 11.

## [0.2.0] - 2026-06-29

### Added

- Player reconnection support for dropped connections.

### Changed

- CI and documentation improvements.
- Dependency and GitHub Actions updates.

### Fixed

- Security patches across the backend.

## [0.1.0] - 2026-06-27

### Added

- Initial public release: a FastAPI + Vue 3 rewrite of the game with a
  hand-drawn UI, real-time multiplayer rooms over WebSockets, guest and
  registered accounts, locale-aware prompt categories, and a deployable
  Docker Compose stack.

[0.2.1]: https://github.com/simonvanlierde/6-second-scribbles/releases/tag/v0.2.1
[0.2.0]: https://github.com/simonvanlierde/6-second-scribbles/releases/tag/v0.2.0
[0.1.0]: https://github.com/simonvanlierde/6-second-scribbles/releases/tag/v0.1.0
