# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Ongoing work since `v0.2.0`: a design-system rebuild of the invite and home
screens, late-joiner support for the shared lobby doodle, hardening of room
disconnect and host-migration handling, security fixes to rate limiting and
guess scoring, and a move to Node 26 / pnpm 11.

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

[Unreleased]: https://github.com/simonvanlierde/6-second-scribbles/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/simonvanlierde/6-second-scribbles/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/simonvanlierde/6-second-scribbles/releases/tag/v0.1.0
