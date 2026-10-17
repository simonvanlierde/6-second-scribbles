# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A logo, favicon, and Apple touch icon.
- A `robots.txt` that keeps crawlers off the API, the WebSocket, room pages, and the internal design-system page.
- A Content Security Policy on the frontend: scripts, styles, fonts, and API and WebSocket calls are limited to the site's own origin.
- `seed_data` modes: `--append` adds only new categories, `--overwrite` replaces the system categories and prompts. A `database-seed` Compose service runs the seeder on demand.
- JSON access logs from the frontend's Caddy server, recording the real visitor IP behind the Cloudflare tunnel.
- End-to-end Playwright tests in CI, against Postgres and Redis.
- A WebSocket load test, `just loadtest`, and [docs/capacity.md](docs/capacity.md) with its result: about 80 rooms of 6 busy players on one backend under the production limits.

### Changed

- Production containers rotate their logs at 3 files of 10 MB each, so Caddy's access log, which holds visitor IPs, no longer grows without limit.
- **Breaking:** `seed_data` without a flag no longer replaces existing system categories. On a database that already has them it makes no changes; pass `--overwrite` for the old behaviour.
- The health endpoint and the OpenAPI document report the release version (0.2.1) instead of a hardcoded 2.0.0.
- The frontend build image runs Node 26 on Debian trixie.
- Backend dependency updates.
- The backend turns each room broadcast into JSON once instead of once per player, which raises the capacity under the production limits from about 70 to about 80 busy rooms.

### Fixed

- After a round, guessers could wait forever on "Waiting for drawing…". The finished drawing was sent as a full-resolution PNG, often over 1 MB on a high-density screen, and the server drops messages over 64 KiB. Drawings are now scaled to at most 1024 px and sent as WebP (JPEG in browsers such as Safari that cannot encode WebP), stepping down until they fit. A player whose message is still too large sees an error instead of nothing.
- Creating a room from the home page failed in production: the backend redirected `POST /api/rooms` to an `http://` URL, which the browser blocked on the HTTPS site. The backend now trusts the forwarded scheme from Caddy.
- Rooms could split in production: the backend ran four worker processes, each with its own in-memory rooms, so a player could create a room on one worker and connect to another. It now runs a single worker.
- Production builds could bake a local `VITE_BACKEND_HOST` into the bundle, sending plain `http://` requests from the HTTPS page. The bundle now always derives the backend from the page's own address.
- The production Redis service now restarts after a crash or host reboot.
- Local `dev-*` and `down-clean` recipes no longer act on the production stack when `COMPOSE_FILE` points at it.
- The page language (`<html lang>`) now follows the chosen language instead of staying English, so screen readers read the text with the right voice and pronunciation.
- A player could replace another player's drawing on everyone else's screen by sending a stroke with that player's id, and a socket that had not joined could still relay strokes to the room. The server now drops strokes from sockets that have not joined and stamps each relay with the sender's own id.
- Rooms nobody ever joined, such as a created code left unused, and rooms restored from Redis after a restart never expired, so they piled up until the 500-room cap refused new rooms. Both now expire after the normal 5-minute empty-room TTL.
- Room-creation and login rate limits in production counted every visitor as one client: the backend read the last `X-Forwarded-For` entry, which Caddy filled with the Cloudflare tunnel container's address. Caddy now forwards the visitor's own IP.
- Any player could take over a guest's seat, and with it their score and prompts, by joining with that guest's player id, which every roster shows. The browser now keeps a private rejoin key next to its player id, and the server refuses a join for a known seat unless it carries the key the seat's first join used.
- Every player received everyone's prompts at the start of a round, so a player could read the answers from the network traffic. Each player now receives only their own card.
- In Safari the favicon lost its colours: the page's Content Security Policy was also sent with the SVG favicon and blocked the `<style>` inside it. SVG files now get their own policy that allows only inline styles.
- A browser set to Chinese (for example `zh-CN` or `zh-TW`) started in English, because only the base language `zh` was kept and the app has no plain `zh`. It now picks Simplified or Traditional Chinese from the browser's language tag.

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

[Unreleased]: https://github.com/simonvanlierde/6-second-scribbles/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/simonvanlierde/6-second-scribbles/releases/tag/v0.2.1
[0.2.0]: https://github.com/simonvanlierde/6-second-scribbles/releases/tag/v0.2.0
[0.1.0]: https://github.com/simonvanlierde/6-second-scribbles/releases/tag/v0.1.0
