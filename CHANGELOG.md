# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Upgrade notes

- A migration drops six database indexes that duplicated unique constraints or were never queried. It drops them concurrently, so it takes no long table lock.
- The backend images run as uid and gid 1001 instead of 1000. Directories you bind-mount into the seed or translate containers must be writable by 1001; the dev Compose file runs the seed container as your own uid.
- `/api/health` now answers HTTP 503, with the same JSON body, while the database or Redis is unreachable. A monitor that reads only the status code now sees an outage; Compose marks the backend unhealthy after 60 to 90 s of it, and `docker compose up --wait` fails on a degraded stack.
- Rolling back to 0.2.x drops every open room: rooms saved by this release carry fields that 0.2.x refuses to load. The database has no new migrations since 0.2.1 and rolls back safely.
- The JSONB translations migration (`b2a7f484d1a9`) can no longer be downgraded. Restore a backup or re-seed instead.
- Migrations now give up after waiting 3 s for a lock or running one statement for 60 s, so a deploy cannot stall the backend that is still serving. Rerun the deploy if one gives up.
- The backend runs a single worker, and a network may hold at most 5 open rooms (`MAX_ROOMS_PER_CLIENT`).
- The `AUTH_REGISTER_*`, `AUTH_LOGIN_*` and `CATEGORY_MUTATION_*` settings are gone. Remove them from `.env` files.
- Deploy with `docker compose build --pull`, `docker compose pull --ignore-buildable`, then `docker compose up -d` (`just up-prod` does this), so base and service images pick up security fixes.

### Added

- A logo, favicon, and Apple touch icon.
- A `robots.txt` that keeps crawlers off the API, the WebSocket, room pages, and the internal design-system page.
- A Content Security Policy on the frontend: scripts, styles, fonts, and API and WebSocket calls are limited to the site's own origin.
- `seed_data` modes: `--append` adds only new categories, `--overwrite` updates the system categories and prompts in place to match the seed file, matched on slug and prompt key. IDs held by open rooms survive a reseed, translation fixes reach existing prompts, only entries removed from the seed file are deleted, and the category caches in Redis are cleared afterwards. A `database-seed` Compose service runs the seeder on demand.
- JSON access logs from the frontend's Caddy server, recording the real visitor IP behind the Cloudflare tunnel.
- End-to-end Playwright tests in CI, against Postgres and Redis.
- A WebSocket load test, `just loadtest`, and [docs/capacity.md](docs/capacity.md) with its result: about 80 rooms of 6 busy players on one backend under the production limits.
- CI builds the production images, starts the production stack and checks its health and hardening, and scans the images with Trivy. A weekly run fails on any new fixable high or critical finding. CI also fails when the models change without a migration.
- OCI labels (source, title, description, licence) on both images.
- Redis keeps its data in a volume, so logins and open rooms survive a recreated Redis container.

### Changed

- Screen readers hear which game phase starts, focus moves to its heading, and the browser tab shows the room screen and round. They hear "10 seconds left" once instead of no countdown.
- Button labels for screen readers follow your language; pen colours and brushes have names, and each reaction button says whose drawing it is for.
- Text follows your browser's font-size setting.
- The chosen pen and avatar colour show a check or an ink outline, so the blue outline only means keyboard focus.
- The frontend build pins corepack to 0.36.0 instead of the latest release.
- A finished game goes back to the lobby by itself 3 minutes after the final results, so a room whose host left can play again. Operators can change the delay with `FINAL_RESULTS_RESTART_SECONDS`. (The host's browser had a timer for this that never fired.)
- Spectators now see a game live, the moment something happens, instead of catching up every 2 seconds. A room takes up to 20 spectators, and they never count toward the player limit.
- Server logs no longer keep full visitor IPs: Caddy masks them to the /24 (IPv4) or /48 (IPv6) network, and the backend no longer writes its own access log or the visitor IP of each WebSocket connection. The About dialog now says what is stored and for how long.
- Production containers rotate their logs at 3 files of 10 MB each, so Caddy's access log, which holds visitor IPs, no longer grows without limit.
- Guest accounts are deleted once their login session has expired (30 days by default), on backend startup and once a day after that.
- **Breaking:** `seed_data` without a flag no longer replaces existing system categories. On a database that already has them it makes no changes; pass `--overwrite` for the old behaviour.
- The server only accepts room codes of 6 letters and digits, the kind it hands out. A WebSocket to any other code is closed before it can create a room, and the room status endpoint answers 422.
- The health endpoint and the OpenAPI document report the release version instead of a hardcoded 2.0.0.
- The frontend build image runs Node 26 on Debian trixie.
- Backend dependency updates.
- The backend turns each room broadcast into JSON once instead of once per player, which raises the capacity under the production limits from about 70 to about 80 busy rooms.
- `start_game` and `settings_update` broadcast the room's stored settings instead of echoing the client's message, so a partial settings change shows everyone the full settings.
- When a network already has too many open rooms or creates rooms too fast, Create room and Quick play say so and suggest closing one, joining a friend's room or waiting a few minutes, instead of "Please try again".
- Contract generation writes one JSON Schema file per direction instead of one per event, and no longer writes `contracts/room-events.json`. The committed contracts are `openapi.json` and the two files in `contracts/jsonschema/`.
- The frontend no longer depends on `@vueuse/core`.

### Removed

- The unused `POST /api/rooms/{room_id}/category-selection` endpoint. It needed no login, had no rate limit, and could return the whole prompt bank.
- The account system: `POST /api/auth/register`, `/login` and `/logout`, and the `argon2-cffi` dependency. No screen used them. Guest sessions are unchanged.
- The unused `GET /api/rooms/random`, `GET /api/categories` and `PATCH /api/me/preferences` endpoints.
- The unused `room_custom_categories_update` WebSocket event and `customCategoryIds` in `room_state`, and the demo account in the local seed data.

### Fixed

- Korean cards showed web-page text as names (for example "이름 *" for leg), Japanese cards included sexual slang, and every language had wrong, English or duplicate accepted answers. The deck is cleaned, and a test now fails on junk text, leftover English answers and an answer that matches two cards in the same category.
- In languages whose plurals do not add -s, a guess could score as another card: German "Eis" (ice cream) counted as "Ei" (egg). Plural endings now follow the guesser's language.
- A round could get stuck in the guessing phase when a reseed removed its category. Those guesses now score 0, and any other scoring error ends the round without points.
- A game where nobody scored crowned a champion; it now says there is no winner, and tied winners all show their avatars.
- The drawing hint was hidden behind the Finish button on laptop screens.
- After you sent your guesses, the guess panel could not be scrolled with the keyboard and lost focus.
- The game-over header showed "0 / 2 players ready".
- Polish player counts used the plural form for 5 or more players for 2 to 4 players as well.
- The loading spinners kept spinning when your system asks for reduced motion.
- The message for a room that briefly turns away new players, after many players left it in a short time, is translated into every language.
- A category without a translation in the room's language is now dealt in the next language it has, so the round still starts.
- Two players could get the same avatar colour. Colours are now unique within a room; a colour picked in settings is kept unless another player already has it.
- A second translation review fixed about 1,700 interface strings, categories and word cards across all 11 languages. Korean, Japanese and Chinese had the most; no word card holds leftover machine-translation debris any more. Production picks up the words after `seed_data --overwrite`.
- A translation review covered the 11 non-English languages. Wrong machine translations in category names, word cards and accepted guesses are corrected (Korean and Japanese had many), French uses "tu" throughout, and Korean uses the polite 해요체. Production picks up the new categories and words only after `seed_data --overwrite`.
- "Connecting…" and "Reconnecting…" were shown in English in every language. A test now fails when a language file misses a key.
- The player count on the room entry page reads "1 player in room", not "1 player", in every language.
- `auto_translate_seed_data` no longer refills an alias list that a reviewer emptied on purpose.
- After a round, guessers could wait forever on "Waiting for drawing…". The finished drawing was sent as a full-resolution PNG, often over 1 MB on a high-density screen, and the server drops messages over 64 KiB. Drawings are now scaled to at most 1024 px and sent as WebP (JPEG in browsers such as Safari that cannot encode WebP), stepping down until they fit. A player whose message is still too large sees an error instead of nothing.
- Creating a room from the home page failed in production: the backend redirected `POST /api/rooms` to an `http://` URL, which the browser blocked on the HTTPS site. The backend now trusts the forwarded scheme from Caddy.
- Rooms could split in production: the backend ran four worker processes, each with its own in-memory rooms, so a player could create a room on one worker and connect to another. It now runs a single worker.
- Production builds could bake a local `VITE_BACKEND_HOST` into the bundle, sending plain `http://` requests from the HTTPS page. The bundle now always derives the backend from the page's own address.
- The production Redis service now restarts after a crash or host reboot.
- Local `dev-*` and `down-clean` recipes no longer act on the production stack when `COMPOSE_FILE` points at it.
- The page language (`<html lang>`) now follows the chosen language instead of staying English, so screen readers read the text with the right voice and pronunciation.
- Rooms nobody ever joined, such as a created code left unused, and rooms restored from Redis after a restart never expired, so they piled up until the 500-room cap refused new rooms. Both now expire after the normal 5-minute empty-room TTL.
- Room-creation and login rate limits in production counted every visitor as one client: the backend read the last `X-Forwarded-For` entry, which Caddy filled with the Cloudflare tunnel container's address. Caddy now forwards the visitor's own IP.
- A restart dropped every saved room when a single one could not be read, for example a room saved by an older release. Unreadable rooms are now skipped one at a time and the rest are restored.
- A round started by the server's timer cancelled itself as it started: the round was not saved after it began, and the server's own drawing timer was never set. Rounds still moved on because each browser presses Finish when its timer runs out, but a player whose browser stayed connected without doing that, such as a locked phone, held the whole room in the drawing phase.
- In Safari the favicon lost its colours: Safari checks the `<style>` inside an SVG favicon against the page's Content Security Policy, which blocks inline styles. The favicon now has no `<style>`: a light and a dark SVG with fixed colours, picked by the browser's colour scheme.
- A browser set to Chinese (for example `zh-CN` or `zh-TW`) started in English, because only the base language `zh` was kept and the app has no plain `zh`. It now picks Simplified or Traditional Chinese from the browser's language tag.
- In dark mode the drawing canvas was dark, so the default black pen was nearly invisible, and drawings made in dark mode showed up as dark tiles for everyone else. The canvas is now light paper in both themes, so every drawing looks the same to every player. The white pen now draws in paper colour in both themes.
- In dark mode the lobby player list was unreadable: names sat on a light grey row, and the host's Kick player button had no background, so it showed only as faint white text. The list now uses the game's own cards, labels and buttons in both themes.
- On phones the settings button covered the round number and score in the game header. The header now leaves room for it.
- Red text, such as the stepper buttons, the Advanced Settings link, highlight labels and standings ranks, was hard to read in light mode. It now uses a darker red that is easy to read in both themes.
- In dark mode your own score in the standings and the name and detail on the yellow highlight card were pale text on yellow. They now use dark ink there.
- Every line uvicorn logged, such as startup messages, appeared twice in the backend log, once as plain text and once as JSON.
- In a short browser window on a laptop, the Finish button sat below the word card, out of view, until the player scrolled the card. It now stays at the bottom of the card column.
- Someone turned away because a room already had 20 spectators saw the server's English message whatever their language. The message is now translated.
- On a phone the Finish button sat below the screen during drawing, under the word list and the canvas. It now stays pinned to the bottom. Buttons that were small to tap on a touch screen (the lobby doodle colours and sizes, the settings steppers, Kick player and Advanced Settings) are now at least 44 px, and so are the words on the drawing card on larger screens.
- Scoring treated a guess differently on a second pass when an accent mark sat next to a space, and counted "s", "es" and "ing" as matches for each other.
- In dark mode the winner's name and the "Game stats" heading were unreadable on the results screen, the selected brush size showed no dot, the lobby's "Room code" label was faint, and drawing thumbnails had dark bars around them.
- The ready tick in the game header wrapped onto its own line.
- The home page "How to Play" and "About" links and the settings language picker were 40 px tall; they are now 44 px.

### Security

- The frontend container runs Caddy as an unprivileged user with every Linux capability dropped, instead of as root with `NET_BIND_SERVICE`. It still listens on port 80, so the Cloudflare tunnel needs no change.
- A player could replace another player's drawing on everyone else's screen by sending a stroke with that player's id, and a socket that had not joined could still relay strokes to the room. The server now drops strokes from sockets that have not joined and stamps each relay with the sender's own id.
- Any player could take over a guest's seat, and with it their score and prompts, by joining with that guest's player id, which every roster shows. The browser now keeps a private rejoin key next to its player id, and the server refuses a join for a known seat unless it carries the key the seat's first join used.
- Every player received everyone's prompts at the start of a round, so a player could read the answers from the network traffic. Each player now receives only their own card.
- A modified client could deal its own cards or force the guessing phase: the host-only `start_round` and `start_guessing` commands still worked, although the app never sends them. They are removed, together with the unused `round_complete` and `game_complete` client events, and rounds are now dealt by the server only.
- A refresh in the lobby released the player's seat, so someone else could claim their player id with a new rejoin key in the moment they were gone, and lock them out. The seat stays bound to its owner's key until they leave on purpose or are kicked; a room keeps these bindings for at most 40 departed players.
- During a Redis outage the backend wrote session ids, which work as 30-day login tokens, into its error log. It no longer logs them.
- One player could freeze the server for every room by filling the lobby drawpad: each room snapshot could grow to tens of MB. The shared doodle now keeps at most 20,000 points (the oldest strokes go first), names, ids and stroke styles have length limits, and each connection gets at most 5 full room snapshots per 5 seconds.
- One player whose connection stopped reading could hold up every message and timer in their room. A send now gives up after 5 seconds, and that player is disconnected so their browser reconnects.
- A player voted out of a public room, or removed by the host, could rejoin straight away. The room now refuses that player, and their account if they were signed in, until it closes.
- One visitor could fill all 500 rooms and lock everyone else out with "Server at capacity". A network may now hold at most 5 open rooms it created (IPv6 addresses count per /64); players and sockets are not limited, so a household on one Wi-Fi can still play together.
- The server now rejects game settings outside the lobby's limits (1 to 10 rounds, 15 to 180 s timers) with a protocol error. Before, a modified client could set a million rounds or a 1 s timer.
- A burst of throwaway joins could push out a guest's saved seat in the lobby and let someone else take it. Seats of players who left in the last 10 minutes are now kept; while 40 of them are held, new players are asked to try again in a few minutes.
- The frontend image moves to Caddy 2.11 on Alpine 3.23 and installs Alpine updates at build time, which fixes 6 critical and 93 high findings in its base. The backend image no longer contains pip or curl; its healthcheck uses Python.
- The Cloudflare tunnel image moves from a June build to cloudflared 2026.10.0, which fixes 17 high findings.
- Production containers run with read-only root file systems, no Linux capabilities and `no-new-privileges`; the database also gets `no-new-privileges` and a 512-process limit.

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
[0.2.1]: https://github.com/simonvanlierde/6-second-scribbles/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/simonvanlierde/6-second-scribbles/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/simonvanlierde/6-second-scribbles/releases/tag/v0.1.0
