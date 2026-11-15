---
name: Six Second Scribbles
description: A paper-notebook party game with hard-offset stickers today, heading for a chaotic sketchbook.
colors:
  paper: "#fdfbf7"
  card: "#ffffff"
  ink: "#3a332c"
  ink-muted: "#6b6459"
  marker-red: "#f36161"
  primary-strong: "#d23c3c"
  primary-text: "#c53030"
  ballpoint-blue: "#2d5da1"
  highlighter-yellow: "#fff9c4"
  amber: "#ffd27a"
  meadow-green: "#b5e6b5"
  ink-fixed: "#3a332c"
  drawing-paper: "#fdfbf7"
  avatar-coral: "#ffb4a2"
  avatar-mint: "#b5e6b5"
  avatar-sky: "#add8e6"
  avatar-sun: "#ffe08a"
  avatar-lilac: "#e0bbff"
  avatar-peach: "#ffcba4"
  paper-dark: "#1a1614"
  card-dark: "#231e1b"
  ink-dark: "#e6ddcb"
  ink-muted-dark: "#9f958a"
  marker-red-dark: "#f06a6a"
  ballpoint-blue-dark: "#7ba4e6"
  highlighter-yellow-dark: "#ffe066"
  amber-dark: "#f0b84e"
  meadow-green-dark: "#9cdb9c"
typography:
  display-lg:
    fontFamily: "Kalam, Caveat, system-ui, sans-serif"
    fontSize: "3.5rem"
    fontWeight: 700
    lineHeight: 1.15
  display-md:
    fontFamily: "Kalam, Caveat, system-ui, sans-serif"
    fontSize: "2.5rem"
    fontWeight: 700
    lineHeight: 1.15
  display-sm:
    fontFamily: "Kalam, Caveat, system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.15
  heading-lg:
    fontFamily: "Kalam, Caveat, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
  heading-md:
    fontFamily: "Kalam, Caveat, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 700
  heading-sm:
    fontFamily: "Kalam, Caveat, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
  body-lg:
    fontFamily: "Patrick Hand, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.5
  body-md:
    fontFamily: "Patrick Hand, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label-md:
    fontFamily: "Patrick Hand, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
  label-sm:
    fontFamily: "Patrick Hand, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
  room-code:
    fontFamily: "ui-monospace, SFMono-Regular, JetBrains Mono, monospace"
    fontSize: "1.6rem"
    fontWeight: 700
    letterSpacing: "0.4em"
rounded:
  card: "16px 22px 14px 18px"
  button: "14px 22px 16px 12px"
  input: "14px 18px 12px 16px"
  pill: "8px 12px 8px 12px"
  avatar: "11px 14px 10px 13px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "20px"
  "6": "24px"
  "8": "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary-strong}"
    textColor: "#ffffff"
    typography: "{typography.heading-sm}"
    rounded: "{rounded.button}"
    padding: "12px 18px"
    height: "44px"
  button-success:
    backgroundColor: "{colors.meadow-green}"
    textColor: "{colors.ink-fixed}"
    rounded: "{rounded.button}"
    padding: "12px 18px"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "12px 18px"
    height: "44px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ballpoint-blue}"
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "16px"
  card-postit:
    backgroundColor: "{colors.highlighter-yellow}"
    textColor: "{colors.ink-fixed}"
    rounded: "{rounded.card}"
    padding: "16px"
  input:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.body-md}"
    rounded: "{rounded.input}"
    padding: "10px 14px"
    height: "44px"
  input-code:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.room-code}"
    rounded: "14px"
  pill:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.pill}"
  timer:
    backgroundColor: "{colors.highlighter-yellow}"
    textColor: "{colors.ink-fixed}"
    typography: "{typography.display-sm}"
  timer-urgent:
    backgroundColor: "{colors.primary-strong}"
    textColor: "#ffffff"
---

# Design System: Six Second Scribbles

Source of truth for tokens is `frontend/src/styles/tokens.css`; components are the `Hd*` set in
`frontend/src/components/ui/`, shown at `/__ds`. The YAML header holds the light value of every
colour and the `-dark` value where the app swaps it with `light-dark()`. Product context is in
[PRODUCT.md](PRODUCT.md); the approved sequence (portrait play, reveal wall, keepsakes) is in
[docs/roadmap.md](docs/roadmap.md). This file describes the system as it is shipped, then the
direction step 2 of the roadmap moves it toward.

## Overview

<!-- rumdl-disable-next-line MD036 -->
**Creative North Star: "The Chaotic Sketchbook"**

Today the app is a tidy paper notebook: warm off-white pages, ink-brown outlines, wobbly corners,
hard-offset shadows like cut-out stickers and a yellow post-it for tips. Display type is handwritten
(Kalam), body is a friendly hand (Patrick Hand), the tone is "Doodle. Guess. Laugh."

The approved direction keeps that material world and turns the volume up where friends laugh:
rough marks, oversized handwriting and unruly motion on the drawing rush and the reveal, while
every control stays predictable and every word stays legible. Chaos belongs to the artwork and to
entrances. Buttons, inputs, timers and prompts hold still, keep a 44 px target and keep their
contrast.

Mode: the in-room screens are Operate (finish a task under time pressure). The reveal wall and the
game-night sheet are Experience (the drawings lead and the chrome recedes).

**Key Characteristics:**

- Paper ground, ink-brown outline on everything that can be touched, one red for the action.
- Wobbly four-value corner radii and small fixed rotations, never a perfect rectangle.
- Hard offset shadows with no blur, in ink colour.
- Handwritten display type for names, headings and numbers; body hand for reading.
- Dark theme is the same notebook by lamplight: cream ink on near-black paper, shadows turn cream.
- The drawing canvas is light paper in both themes, so every player sees the same drawing.

## Colors

A paper, ink and marker palette. One saturated red (primary-strong) carries the main action, yellow
is the highlighter for tips and the timer, green is "go / ready / done", blue is the ballpoint used
for links and the focus ring.

### Primary

- **Marker Red** (#f36161): strokes, borders, fills, wavy strike-through on done words. Reaches only
  3.0:1 on paper, so it never carries text.
- **Strong Marker Red** (#d23c3c): every red surface that holds white text (primary button, toast,
  urgent timer, champion ribbon). White on it is 4.7:1.
- **Text Red** (#c53030 light, #f06a6a dark): red text on paper or card, 5.3:1 and 6.0:1.

### Secondary

- **Ballpoint Blue** (#2d5da1 light, #7ba4e6 dark): links, ghost buttons, the 3 px focus ring.
- **Meadow Green** (#b5e6b5): success button, ready state, point gain badges. Ink on it is 8.9:1.

### Tertiary

- **Highlighter Yellow** (#fff9c4 light, #ffe066 dark): post-it cards, the timer, the room-code
  chip. Always carries `ink-fixed`, so it stays dark text in both themes.
- **Amber** (#ffd27a): the champion card wash and warm highlights.

### Neutral

- **Paper** (#fdfbf7, #1a1614 dark): page ground, plus a 4 % multiply paper-grain texture.
- **Card** (#ffffff, #231e1b dark): raised surfaces.
- **Ink** (#3a332c, #e6ddcb dark): text, outlines, hard shadows.
- **Ink Muted** (#6b6459, #9f958a dark): secondary text, 5.7:1 and 6.1:1. Placeholders use it at
  70 % opacity, which drops to 3.1:1.
- **Ink Fixed** (#3a332c): text on surfaces that stay light in both themes (post-its, green
  badges, avatars).
- **Drawing Paper** (#fdfbf7): the canvas and every thumbnail of a drawing. Mirrors
  `DRAWING_PAPER` in `config/drawing.ts`.
- **Avatar palette** (coral, mint, sky, sun, lilac, peach): decorative, identical in both themes,
  always with ink-fixed initials.

### Named Rules

**The One Red Rule.** Red is the action. One filled red button per screen region; a second red
surface (kick, danger, ribbon) must be smaller or quieter than the main action.
**The Paper Stays Paper Rule.** Drawings are shown on light paper in both themes. Never tint or
invert a drawing to suit the theme.
**The Text-Safe Red Rule.** Bright marker red is for strokes and fills. Any red text uses Text Red.

## Typography

**Display Font:** Kalam (700), fallback Caveat, system-ui
**Body Font:** Patrick Hand (400), fallback system-ui
**Label/Mono Font:** ui-monospace stack, used only for room codes

**Character:** Two hands on one page. Kalam is the loud marker for headings, buttons and numbers;
Patrick Hand is the quiet ballpoint for sentences. Sizes are in rem so they follow the browser
setting.

### Hierarchy

- **Display** (700, 3.5 / 2.5 / 2 rem, 1.15): home title, game-over banner, timer digits.
- **Headline** (700, 1.75 / 1.375 / 1.125 rem): view titles, card titles, uppercase section
  headings with 0.04 em tracking.
- **Body** (400, 1.125 / 1 rem, 1.5): prompts, guesses, descriptions.
- **Label** (400, 0.875 / 0.8125 rem): pills, scores, field labels. 13 px is the floor today.
- **Room code** (mono 700, 1.6 rem, 0.4 em tracking, uppercase): the join field and code chips.

### Named Rules

**The Legible Handwriting Rule.** Handwriting fonts carry large or short text. Anything a player
must read under time pressure (prompts, guesses, scores) is body size or larger.
**The Oversize Moment Rule (target).** Step 2 may set one word per reveal, such as a guess or a
name, at display size. Controls never grow with it.

## Layout

Single page column, desktop first. Views centre at 1100 to 1200 px (`max-width`), pad 16 to 24 px
and use a two-column grid (`1.4fr 1fr` on results, `minmax(300px, 500px) 1fr` in the lobby) that
collapses to one column at 768 px (900 px in the lobby). Spacing follows a 4 px base
(4, 8, 12, 16, 20, 24, 32). In-game screens (drawing, guessing) lock to `100dvh` with an internal
scroll, under a dark game header that holds back, mute, timer, round and score.

Phones (target of roadmap step 1): the prompt list, toolbar, canvas and Finish stack in one column.
The canvas keeps at least 260 px of height, Finish stays in view, and the guess list scrolls inside
its panel while Submit stays outside it.

Reveal wall (target of step 2): all drawings of the round on one wall, first in the page order
of round results, tap-to-enlarge on phones, short staggered entrance.

## Elevation & Depth

Flat paper with sticker-style lift. Depth is a hard offset shadow in ink colour with no blur, plus
a small fixed rotation, so every surface looks cut out and stuck down. Pressing a button moves it
into its shadow (translate 3 px, shadow removed). In dark mode the ink is cream, so shadows read as
cream offsets.

### Shadow Vocabulary

- **Card** (`box-shadow: 4px 4px 0 var(--color-ink)`): cards, drawing frames, thumbnails.
- **Button** (`3px 3px 0 var(--color-ink)`): buttons and icon buttons.
- **Pill** (`2px 2px 0 var(--color-ink)`): pills, badges.
- **Avatar** (`2.5px 2.5px 0 var(--color-ink)`): avatars.

### Named Rules

**The No Blur Rule.** Shadows are hard offsets. There are no soft or glow shadows anywhere.
**The Pressed Paper Rule.** The press state removes the shadow; it is the only state feedback that
moves a control.

## Shapes

Wobbly, hand-cut corners: every radius has four different values (card 16 22 14 18, button 14 22 16 12,
input 14 18 12 16, pill 8 12 8 12, avatar 11 14 10 13). Outlines are 2 px (inputs), 2.5 px (cards,
buttons) in ink. Fixed rotations: cards -0.4 deg, buttons -0.5 deg, post-its -1.2 deg. The code
field and the room-code chip use dashed outlines, like a tear-off ticket. The focus ring is a 3 px
ballpoint-blue outline with a 2 px offset.

## Components

### Buttons

- **Shape:** wobbly 14/22/16/12 radius, 2.5 px ink border, 3 px hard shadow, -0.5 deg tilt.
- **Primary:** Strong Marker Red, white text, Kalam 700 1.05 rem, 12 x 18 px padding, 44 px minimum.
- **Success:** Meadow Green with ink-fixed text (Join, Finish, Ready).
- **Secondary:** card ground with ink text (Back, Leave).
- **Ghost:** no border, ballpoint blue text.
- **Disabled:** 45 % opacity, `not-allowed`. Reads as washed out; pair with a visible reason.

### Cards / Containers

- **Corner Style:** wobbly 16/22/14/18, 2.5 px ink border.
- **Background:** card, or highlighter yellow for the post-it variant (tips, highlights, game stats).
- **Shadow Strategy:** Card shadow, -0.4 deg tilt (-1.2 deg for post-its).
- **Internal Padding:** 16 px.

### Inputs / Fields

- **Style:** card ground, 2 px ink border, wobbly 14/18/12/16, faint inset shadow, 44 px minimum.
- **Code variant:** monospace 1.6 rem, 0.4 em tracking, dashed border, centred, uppercase.
- **Focus:** universal 3 px blue ring.

### Navigation

- **Game header:** an ink-coloured bar (inverts in dark mode) with a back button, mute, the yellow
  timer, round and score. The timer pulses on the last 10 s, in red.
- **Settings:** a gear button fixed top right on every screen.

### Drawing canvas (signature)

- Light drawing paper with a faint dot grid, 2.5 px ink border and card shadow. Toolbar above it:
  six pen colours, three sizes, undo and clear. Prompt list beside it (stacked above it on phones)
  with tap-to-cross-off in wavy marker red.

### Drawing thumbnail and gallery

- 4:3 drawing-paper tile, card shadow, avatar tag at the top left, a yellow name label below and
  a download button over the image. Used for the round reveal and the final gallery today; the
  base of the step 2 wall.

## Do's and Don'ts

### Do

- **Do** outline every touchable surface in ink and give it a hard offset shadow and a wobbly radius.
- **Do** keep touch targets at 44 px or more, and at 24 px at the very least on a short laptop screen.
- **Do** put white text only on Strong Marker Red (#d23c3c), never on bright marker red.
- **Do** give the post-it, the avatar and every green or yellow badge `ink-fixed` text so they read in both themes.
- **Do** read tokens through the semantic aliases (`--color-bg`, `--color-text`, `--color-primary`).
- **Do** keep the drawing on light paper and the roughness in the art, entrances and headings.
- **Do** honour `prefers-reduced-motion`: the motion tokens drop to 0 ms and keyframes are disabled.

### Don't

- **Don't** add blur shadows, gradients behind text.
- **Don't** set text at 13 px or less for anything a player must read during a round.
- **Don't** make a second red surface (kick, danger) as loud as the main action.
- **Don't** rotate or wobble controls further than the current token values; motion that moves
  where a button sits makes it hard to hit.
- **Don't** hide the next action below the fold on a 320 x 568 phone.
- **Don't** use the spring ease (0.34, 1.56, 0.64, 1) on anything but small acknowledgements;
  prefer `--ease-out` for entrances.
