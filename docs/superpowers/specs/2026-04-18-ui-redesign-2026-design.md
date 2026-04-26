# 6 Second Scribbles · 2026 UI Redesign — Design Spec

**Date:** 2026-04-18
**Status:** Approved for implementation planning
**Scope:** Full reimagining (visual + interaction + IA + new features)

---

## 1. Goal

Replace the current generic "purple-blue gradient SaaS" presentation of 6 Second Scribbles with a coherent, on-brand experience that:

- expresses the game's identity (a drawing-and-guessing party game) rather than hiding behind a generic template;
- elevates the gameplay moments (round start, last-10-seconds tension, reveal, winner) through deliberate motion, sound, and layout;
- works equally well on mobile portrait phones (375 px) and on desktop browsers (≥1280 px) — no separate spectator/TV view;
- introduces a small set of high-leverage new features (player avatars, anonymous quick-play, round highlights, ambient sound, live reactions during reveal, drawing gallery, per-drawing PNG export).

The redesign is greenfield: tech stack is open and nothing in the current product is off-limits.

## 2. Non-goals

- No new game mechanics (round flow, scoring, prompt structure, room-code system stay as-is).
- No backend rewrites for redesign reasons; backend changes only where a new feature requires it (avatar storage, reactions, highlights computation).
- No persistent game archive / replayable rooms — deferred to a future feature (see §11).
- No drawing-stroke replay (was on the candidate list, dropped).
- No leaderboard share-card PNG (was on the candidate list, replaced by per-drawing PNG export).
- No custom prompt packs.
- No watch-only mid-game join.

## 3. Personality direction

**Direction: Playful hand-drawn** (one of four explored: hand-drawn, neo-arcade, glassmorphic, refined editorial).

**Reasoning:** the product *is* a drawing game; the interface should feel like the same hand that makes the drawings made the buttons. Warm cream paper, ink black borders, hard offset shadows, slight rotation on cards, marker accents. Reads as "friends on a couch with a notebook" rather than "premium SaaS dashboard". Sourced from the `Sketch Hand-Drawn (Mobile)` style in the ui-ux-pro-max database.

## 4. Design tokens

### 4.1 Color (light mode — primary)

|Token|Hex|Role|
|---|---|---|
|`--color-paper`|`#FDFBF7`|App background (warm paper)|
|`--color-card`|`#FFFFFF`|Card surface|
|`--color-ink`|`#2D2D2D`|All text, borders, hard-offset shadow|
|`--color-marker-red`|`#FF4D4D`|Primary accent (CTAs, danger, urgent timer, highlight ribbons)|
|`--color-ballpoint-blue`|`#2D5DA1`|Secondary accent (links, info, annotations)|
|`--color-highlighter-yellow`|`#FFF9C4`|Tertiary accent (room-code, post-its, "you" rows)|
|`--color-meadow-green`|`#B5E6B5`|Success, "ready", "join" CTA|
|Avatar palette|`#FFB4A2` `#B5E6B5` `#ADD8E6` `#FFE08A` `#E0BBFF` `#FFCBA4`|6 colours assignable per player|

**Contrast targets:** ink (#2D2D2D) on paper (#FDFBF7) is 13.6:1 — passes AAA. Marker red on paper is 4.6:1 (AA for body text, used only for headings & icons). Avatar colours are decorative only — never sole carrier of meaning.

### 4.2 Color (dark mode)

|Token|Hex|Role|
|---|---|---|
|`--color-paper`|`#1A1614`|Warm dark cream|
|`--color-card`|`#231E1B`|Card surface|
|`--color-ink`|`#F2EDE2`|Chalk|
|`--color-marker-red`|`#FF6B6B`|Lifted saturation for dark surfaces|
|`--color-ballpoint-blue`|`#7BA4E6`|Lifted|
|`--color-highlighter-yellow`|`#FFE066`|Lifted|
|`--color-meadow-green`|`#9CDB9C`|Lifted|

Dark mode is "blackboard" — same hard-offset shadow logic, just chalk-on-board. Toggled by user preference (default: system).

### 4.3 Typography

|Role|Family|Weight|Size scale|
|---|---|---|---|
|Display|`Kalam`|700|32 / 40 / 56 px|
|Heading|`Kalam`|700|18 / 22 / 28 px|
|Body|`Patrick Hand`|400|16 / 18 px|
|Label / pill|`Patrick Hand`|400|13 / 14 px|
|Mono / room-code|system mono (`ui-monospace`)|400|tabular figures, 0.4em letter-spacing|

Self-hosted via `@fontsource/kalam` + `@fontsource/patrick-hand`. `font-display: swap`. Fallback stack: `'Kalam', 'Caveat', system-ui, sans-serif` and `'Patrick Hand', system-ui, sans-serif`.

### 4.4 Effects

- **Border radius**: wobbly, four different values per corner. Tokens `--r-card: 16px 22px 14px 18px`, `--r-button: 14px 22px 16px 12px`, `--r-input: 14px 18px 12px 16px`. Each instance can rotate values to look hand-drawn.
- **Border width**: 2 px on inputs, 2.5 px on cards & buttons, all solid `--color-ink`.
- **Shadow**: hard offset, no blur. Token `--shadow-card: 4px 4px 0 var(--color-ink)`. On press, button translates `(4px, 4px)` and shadow flattens to `0 0 0` — the button "sits down".
- **Rotation**: cards and buttons get a randomised micro-rotation between `-1.2deg` and `1.2deg` at render. Per-element `--rotate` CSS variable so designers can override.
- **Texture**: subtle paper grain via SVG noise filter, applied as a `body::before` overlay at `opacity: 0.04`.
- **Decorative SVG**: tape strips, tacks, scribbled arrows used sparingly as page accents (registered as components, not arbitrary inline SVG).

### 4.5 Motion

- **Duration tokens**: `--motion-fast: 150ms`, `--motion-base: 220ms`, `--motion-slow: 360ms`.
- **Easing tokens**:
  - `--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1)` (default for press/release)
  - `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)` (entries)
  - `--ease-in: cubic-bezier(0.7, 0, 0.84, 0)` (exits)
- **Patterns**:
  - **Press**: button translates into shadow + shadow flattens, `--motion-fast` `--ease-spring`.
  - **Card entry**: fade + translateY(8px), staggered 40 ms per item.
  - **Reveal (round results)**: drawing thumbnails scale-in from 0.96 → 1.0 with stagger, `--motion-base` `--ease-spring`.
  - **Error / invalid input**: jiggle (-2°↔2°, 4 cycles, `--motion-base`).
  - **Timer urgent state** (≤10 s): swap to red marker style, slow heartbeat scale 1.0 → 1.04 → 1.0 at 1 Hz.
- **Reduced motion**: all of the above are no-ops under `prefers-reduced-motion: reduce`. State changes still happen (colour/opacity), but transforms are skipped.

### 4.6 Iconography

- **Library**: Lucide (already in project — keep). 1.75 px stroke, 20 px default size.
- **Hard rule**: zero emoji in structural UI. Emoji are reserved for **player reactions only** (the 5 reaction icons during round results).
- Icons are wrapped in a hand-drawn chip when used as a control (rotation + offset shadow); naked when inline.

### 4.7 Sound (optional, off by default)

- **Library**: Howler.js.
- **Cues**: round-start chime, last-10s tick, reveal stinger, winner fanfare, button press click.
- **Files**: 6 short OGG samples, ~5 KB each, lazy-loaded on first user interaction.
- **Toggle**: persistent in localStorage, surfaced in the in-game header next to leave button.

## 5. Component primitives

To be built in `frontend/src/components/ui/` as the design-system core. Each is a small Vue 3 SFC with strict prop API.

|Component|Purpose|Variants|
|---|---|---|
|`HdButton`|All clickable actions|`primary` (red marker), `secondary` (white), `success` (green), `ghost` (underlined link)|
|`HdCard`|Surface for grouped content|`default`, `postit` (yellow, more rotation, paper-tape shadow)|
|`HdInput`|Text input|`default`, `code` (dashed border, mono, large)|
|`HdAvatar`|Player identity|size `sm` `md` `lg`, accepts colour + initial (or doodle face SVG in future)|
|`HdTimer`|Countdown timer|`calm`, `urgent` (auto-switches at threshold prop)|
|`HdPill`|Small status / metadata chips|`default`, `info`, `success`|
|`HdReactionPad`|5-icon emoji reaction tray|emits `react` event with key|
|`HdToast`|Notification|`info`, `success`, `error`|
|`HdDialog`|Modal confirm|`default`, `danger`|
|`HdIconButton`|Icon-only button (gear, leave arrow, copy, close) — small round/rotated chip with accessible label|`default`, `ghost`|
|`HdSidepanel`|Slide-in right panel (desktop) / bottom sheet (mobile) with focus trap + scrim|`right` (default), `bottom`|
|`HdSegmented`|Segmented radio control (for Light / Dark / Auto theme, future small pickers)|generic, N options|

All components forward `class` and `style` so consumers can theme/position. All have visible focus rings (`outline: 3px solid var(--color-ballpoint-blue); outline-offset: 2px`). All meet 44 × 44 pt minimum touch target. `HdIconButton` hides its label visually but exposes it via `aria-label`.

## 6. Screen specs

For each screen: layout, components used, behavioural notes, mobile vs. desktop differences.

### 6.1 Home (`/`)

**Purpose:** Get a player into a room as fast as possible.

**Layout (desktop):** centred column, max-width 560 px. Top-right corner of the page holds a **settings gear icon** (see §6.7) — identity/locale/theme live there, not inline. Below the top bar: display wordmark "6 Second Scribbles" (Kalam, two-line) + tagline "Doodle. Guess. Laugh." Single primary `HdCard` containing:

1. Two side-by-side primary actions: **Start a room** (red), **Find a random** (white).
2. Room-code `HdInput` (code variant) + **Join with code** (green) below.
3. **Quick-play** strip — yellow post-it: "Just play. No name, no fuss." with a small Quick-play CTA.

**Mobile:** same composition, single column, all stacked. Wordmark size drops to 32 px display. Gear icon stays top-right inside the safe area.

**New:** quick-play (auto-generates avatar + name + creates/joins a public room in one tap); identity/locale/theme moved into a global settings panel (§6.7) reachable from the gear icon.

**Removed:** "How to play" no longer expanded by default — moved to a footer link (`?` icon) opens a `HdDialog`. The "You" identity row is gone — its contents live in the settings panel.

### 6.2 Lobby (`/room/:code`)

**Purpose:** Wait for players, see who's there, start the game.

**Layout (desktop):** topbar with **leave** + **room code** chip (yellow highlighter, dashed border, copyable). Two-column body (1.1fr / 1fr):

- **Left card** — player list (avatar + name + role badge), inline collapsible game settings (difficulty / rounds / drawing time / guessing time), then the **Start game** primary CTA at the bottom.
- **Right column** — doodle pad preview (existing functionality, re-skinned) + a yellow post-it with a usage hint.

**Mobile:** single-column stack. Doodle pad collapses to a "Show pad" toggle.

**New:** avatar colours visible everywhere (lobby, game, results); room-code is now a yellow highlighter chip with a copy affordance.

### 6.3 Drawing phase

**Purpose:** Let the drawer scribble through a category as fast as they can; convey time pressure.

**Layout (desktop):** dark ink-bar header (`--color-ink` background, paper text) with leave / sound-toggle on left, large `HdTimer` centre, round + score + ready-count on right. Body splits 220 px sidebar / canvas:

- **Sidebar** — category card with numbered list (items strike through wavily as they're drawn — heuristic: per-stroke item-completion if we can detect, else manual tap), a hint post-it, a **Finish** success button.
- **Canvas** — minimal tool row (5 colour swatches, 3 brush sizes, undo/clear), then the canvas itself with a faint dot grid (paper feel) at 20 px intervals.

**Mobile:** header same. Sidebar collapses above canvas; finish button moves below canvas.

**Behaviour:** at `timeLeft ≤ 10s` the timer flips to red marker style + heartbeat. At 0 s, drawing auto-submits.

### 6.4 Guessing phase

**Purpose:** Look at one player's drawing and submit guesses.

**Layout (desktop):** same dark ink-bar header. Body splits 1.2fr (drawing) / 1fr (guesses):

- **Drawing frame** — header "Maya's drawing" with avatar chip. Stage shows the image on cream background.
- **Guess panel** — header "Your guesses · N / 10". 2-col grid of `HdInput` instances. New input appears as you type. **Submit guesses** primary button. Helper post-it.

**Mobile:** stack vertically; drawing on top, guess panel scrolls below.

**Removed (per feedback):** live reactions during guess phase — only one player guesses each drawing, so reactions here are wasted.

### 6.5 Round results

**Purpose:** Celebrate the round, surface highlights, react to drawings, advance.

**Layout (desktop):** dark header with title + countdown chip. Body has three sections:

1. **Highlights strip** — three rotated highlight cards (best guesser ★, speed demon ⚡, wildest miss 😅). Middle card is yellow post-it variant for rhythm. Each card has a coloured label (red), winner avatar + name, one-line detail.
2. **Round performance + Standings** — 1.4fr / 1fr two-column grid of cards. Performance card lists each player + their score this round. Standings card lists current totals; "you" row is a yellow post-it style.
3. **Drawing reveal grid** *(new — replaces guess-phase reactions)* — every drawing from the round is shown in a small grid. Each drawing has a `HdReactionPad` underneath; when you tap a reaction, it appears on the drawing thumbnail and is broadcast to all players via WebSocket. Reactions accumulate for the duration of the countdown.

**Mobile:** highlights stack, then performance, then standings, then reveal grid.

### 6.6 Final results

**Purpose:** Celebrate the winner, recap the game, allow rematch / exit.

**Layout (desktop):** dark header with "🏁 Game over" + status chip. Body:

1. **Winner card** — large yellow→amber gradient card with a "CHAMPION" red ribbon ("tape" decoration), winner avatar (xl), name, score.
2. **Two-column grid** —
   - Left: final standings card + game-stats post-it (rounds, players, difficulty, total drawings & guesses).
   - Right: *(new, replaces share-card)* **All drawings gallery** — grid of every drawing made, each with the drawer's avatar in the corner. Hover/tap reveals a small download icon → exports just that drawing as a PNG (cream background, ink stroke colour preserved, no other UI). Implementation: client-side via the existing canvas data + a small toPNG helper.
3. **Bottom CTAs** — Play again (red) / New room (white) / Back home (green).

**Mobile:** stack everything vertically; gallery becomes 3-col.

### 6.7 Settings panel (global)

**Purpose:** Centralise per-user preferences behind a single reachable surface — identity, locale, theme, ambient sound, and any future preferences. Replaces the inline "You" chip on Home and the ad-hoc sound toggle in the in-game header.

**Trigger:** a `HdIconButton` with a gear icon in the top-right of every screen (Home, Lobby, Game, Results). The button uses the hand-drawn aesthetic (rotated chip, hard-offset shadow). On the in-game dark-header screens (Drawing / Guessing / Round results / Final results) it sits in the header right cluster next to the leave/score group.

**Presentation:** desktop → right-hand slide-in sidepanel, 360 px wide, full-height, overlays content with a scrim (using `HdDialog`-compatible backdrop). Mobile → bottom-sheet style slide-up (covers 70–90 % of the viewport, swipe-down to dismiss).

**Contents (vertical stack, in order):**

1. **Identity** — `HdAvatar` (lg) + name `HdInput` + locale selector. Editing name updates in-flight (debounced), color chosen via a small avatar-colour picker (6 swatches from the avatar palette).
2. **Theme** — three-option segmented control: Light / Dark / Auto. Writes to a new `useTheme` composable that persists to `localStorage` AND sets `document.documentElement.dataset.theme`.
3. **Sound** — toggle wired to `useSound().enabled`.
4. **About** — small link footer: "How to play", "Source on GitHub", attribution to Hazel Reynolds / Oliver Culley de Lange, license. (Absorbs the content that was in the current footer + the `HowToPlay` collapsible.)

**Component:** new `HdSidepanel` primitive (generic, reusable) + a screen-specific `SettingsPanel.vue` composite that owns the three sections. `HdSidepanel` API: `v-model:open`, `title` prop, `side` prop (`right` | `bottom` — picks sidepanel vs. bottom-sheet responsive behaviour automatically by media query; the prop is just for explicit override).

**Persistence:**

- Name + locale + avatar color → Pinia store persisted via `pinia-plugin-persistedstate` (existing pattern).
- Theme → `localStorage` key `ds:theme` (one of `"light"` / `"dark"` / `""` for auto).
- Sound → already handled by `useSound` (key `ds:sound-enabled`).

**Accessibility:**

- Gear button has `aria-label="Settings"`.
- Sidepanel has `role="dialog"` + `aria-modal="true"` + focus trap while open.
- Escape closes the panel.
- Backdrop click closes.
- Theme segmented control uses native `input[type=radio]` under the hood (keyboard + screen-reader friendly) visually styled as segmented buttons.

## 7. Feature integration map

|Feature|Where it lives|Dependencies|
|---|---|---|
|Player avatars|Home (you-row), Lobby (player list), Drawing/Guessing (header), Results (everywhere)|`HdAvatar` component, store change to persist `playerColor`|
|Anonymous quick-play|Home (yellow post-it strip)|New endpoint `POST /api/rooms/quick-play` (server picks a random open public room or creates one), client auto-generates name + avatar|
|Round highlights|Round results (top strip)|Backend computes per-round on game-state transition; sends as part of the round-results event|
|Live reactions|Round results (drawing-reveal grid only)|New WebSocket events `reaction_send` / `reaction_received`; ephemeral, not persisted|
|Ambient sound|Global (header toggle in-game)|`useSound` composable wrapping Howler; lazy-loaded sample bundle; persisted localStorage flag|
|Drawings gallery|Final results|Client already has all stroke data per drawing; render thumbnails directly|
|Per-drawing PNG export|Final results gallery|`html-to-image` or canvas `toDataURL`; one-tap download|
|Settings panel|Global (gear icon top-right on every screen)|`HdIconButton` + `HdSidepanel` + `HdSegmented` primitives; `useTheme` composable; absorbs identity / locale / theme / sound|

## 8. Architecture & file changes

### 8.1 Frontend structure

```text
frontend/src/
├── components/
│   ├── ui/                # design-system primitives
│   │   ├── HdButton.vue
│   │   ├── HdCard.vue
│   │   ├── HdInput.vue
│   │   ├── HdAvatar.vue
│   │   ├── HdTimer.vue
│   │   ├── HdPill.vue
│   │   ├── HdReactionPad.vue
│   │   ├── HdToast.vue
│   │   ├── HdDialog.vue
│   │   ├── HdIconButton.vue     # NEW (Sprint 1) — icon-only button
│   │   ├── HdSidepanel.vue      # NEW (Sprint 1) — right-slide / bottom-sheet
│   │   └── HdSegmented.vue      # NEW (Sprint 1) — radio segmented control
│   ├── settings/          # NEW (Sprint 1) — settings panel composite
│   │   └── SettingsPanel.vue
│   ├── home/              # screen-specific composites
│   ├── lobby/
│   ├── game/              # drawing + guessing composites
│   └── results/
├── styles/
│   ├── tokens.css         # NEW — all CSS custom properties (color, type, motion)
│   ├── reset.css
│   └── texture.svg        # NEW — paper grain noise filter
├── composables/
│   ├── useSound.ts
│   ├── useAvatar.ts       # colour + initial helpers
│   ├── useReactions.ts
│   └── useTheme.ts        # NEW (Sprint 1) — Light/Dark/Auto + localStorage
└── views/
    └── (existing views, refactored to use new components)
```

### 8.2 Tailwind config

Replace the current ad-hoc `@theme` block in `assets/main.css` with a tokens layer that consumes `styles/tokens.css`. Tailwind utilities continue to compose, but arbitrary-value escapes (`rounded-[28px]`, `shadow-[0_24px...]`) become design-system tokens (`rounded-card`, `shadow-card`).

### 8.3 Backend changes (small)

- **Player model**: add `color` (string, one of 6 token names) and `display_name` (already exists). Avatar colour assigned on join if missing.
- **Round results event**: include a `highlights` field — `{ best_guesser, speed_demon, wildest_miss }` each with `playerId` + `detail`.
- **Quick-play endpoint**: `POST /api/rooms/quick-play` — returns either an existing public room with `< MAX_PLAYERS` or a freshly created one.
- **Reaction WebSocket events**: `reaction_send` (client → server: drawingId, reactionKey) and `reaction_received` (server → all clients in room: same payload + senderId). Not persisted.

### 8.4 Tech stack additions

|Package|Purpose|
|---|---|
|`@fontsource/kalam`, `@fontsource/patrick-hand`|Self-hosted display + body fonts|
|`@vueuse/motion`|Spring physics for press, stagger reveals (alternative: Motion One)|
|`howler`|Ambient sound playback|
|`html-to-image`|Drawing PNG export from canvas data|

No framework changes. Vue 3, Vite, Pinia, Tailwind, vue-i18n, FastAPI, SQLAlchemy, PostgreSQL, Redis, WebSockets all stay.

## 9. Implementation strategy

**Approach 1: Foundations + vertical slices** (selected over big-bang and parallel-routes alternatives).

### Sprint 0 — Foundations (no user-visible change)

- Define `tokens.css` with colour, type, motion, radius, shadow tokens (light + dark).
- Self-host fonts; configure font loading.
- Build the 9 `Hd*` design-system primitives with Storybook-equivalent demo route at `/__ds`.
- Set up `useSound`, `useAvatar`, `useReactions` composables.
- Set up Tailwind config to consume the tokens.
- Establish motion library (`@vueuse/motion`).

### Sprint 1 — Home + Lobby + Settings panel

- Build three new primitives: `HdIconButton`, `HdSidepanel`, `HdSegmented`.
- Build `SettingsPanel` composite (identity + locale + theme + sound + about), wired via a persistent gear icon in a shared app shell so it's reachable from every screen.
- Add `useTheme` composable (Light / Dark / Auto, persisted to `localStorage`, applied via `data-theme` on `<html>`).
- Rebuild `HomeView` and components using new primitives; drop the "You" chip (moves to settings panel).
- Add quick-play (frontend + backend endpoint).
- Add avatar to player identity (frontend + backend `color` field).
- Lobby rebuild including room-code chip, avatar player list, inline settings, gear icon.
- Migrate existing `ToastContainer` and `ConfirmDialog` callers to `HdToast` / `HdDialog`; delete the old files.

### Sprint 2 — Drawing + Guessing

- Rebuild `DrawingPhase` with new dark header, sidebar, dot-grid canvas, redesigned tool row.
- Rebuild `GuessingPhase` with new layout (no reactions).
- Add ambient sound layer (round start, last-10s tick, button click); wire toggle.

### Sprint 3 — Round Results

- Rebuild `RoundResultsView` with highlights strip + reveal grid.
- Add highlights computation backend-side.
- Add reactions on the reveal grid (WebSocket round-trip).

### Sprint 4 — Final Results

- Rebuild `ResultsView` with winner card + two-column grid + gallery.
- Add per-drawing PNG export.

### Sprint 5 — Polish

- Reduced-motion + dark-mode audit on every screen.
- Accessibility pass (focus order, ARIA labels, contrast).
- Visual QA at 375 / 768 / 1024 / 1440 px.
- Performance: bundle-size impact of fonts + sound + motion lib; lazy-load where possible.

### Sequencing rationale

- Sprint 0 builds the system once, so every later sprint is fast and visually coherent.
- Sprints 1–4 are vertically sliced — each ships a complete user-facing change, so we get feedback every sprint.
- Sprint 5 absorbs all the rough edges that only show up across screens.

### Risks

- **Transitional dissonance** (~2–3 sprints where Home looks new but Drawing still doesn't). Mitigation: consider a feature flag if it gets jarring during dogfooding.
- **Font weight on initial paint** — Kalam + Patrick Hand together are ~80 KB compressed. `font-display: swap` masks this; if FOUT is too jarring, fall back to `optional`.
- **Motion library bundle size** — `@vueuse/motion` is ~12 KB; acceptable.
- **Accessibility under "wobbly" aesthetic** — wobbly radii and rotations are decorative; need to ensure focus rings stay rectangular and crisp regardless of element rotation.

## 10. Acceptance criteria

A sprint is "done" when:

1. All visible UI uses only design-system tokens (no arbitrary Tailwind values, no hardcoded hex).
2. Light-mode and dark-mode both pass WCAG AA contrast (4.5:1 body, 3:1 large) — verified with an automated checker on the design-system demo route.
3. All interactive elements have a visible focus ring and are reachable via keyboard.
4. `prefers-reduced-motion: reduce` disables transforms but preserves state changes.
5. Verified visually at 375 px portrait, 768 px portrait, 1024 px landscape, 1440 px landscape.
6. No emoji in structural UI (only in `HdReactionPad`).
7. All new features in scope for that sprint are functional end-to-end (frontend + backend).
8. Existing test suites still pass; new components have at least smoke tests.

## 11. Future / deferred

Worth flagging now so we don't accidentally design ourselves out of them:

- **Persistent game archive** — saving rooms (drawings, scores, highlights) to backend/Redis with a shareable URL `/game/:id` for later viewing. Replaces the "share-card" idea with something genuinely useful. Out of scope for this redesign.
- **Drawing replay** — animate strokes back during round results. Already-recorded data supports it; we just don't render it. Easy addition later.
- **Custom prompt packs** — host adds their own category. Backend lift, deferred.
- **Watch-only mid-game join** — spectator state on backend.
- **Hand-drawn doodle avatar faces** — instead of just initial-on-colour, render small SVG faces. Keep `HdAvatar` API ready for it.
- **Localisation of new copy** — all new strings must use `vue-i18n` keys; defer translation work to after copy is stable.

## 12. Open questions

None blocking. Items to revisit during implementation:

- Final highlights logic. Working definitions: **best guesser** = highest `correctGuesses / totalItems` ratio for the round; **speed demon** = first player to submit a non-empty guess set; **wildest miss** = guess with the highest string-distance from any item in the category, OR (simpler) the player with the most reactions on their drawing if reactions are tracked. Decide during Sprint 3.
- Whether to ship a small set of pre-recorded sound samples or commission them.
- Avatar colour assignment — round-robin vs. user-pickable in Sprint 1; can defer the picker to a later sprint.
