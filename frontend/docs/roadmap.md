# Product roadmap

Approved on 2026-11-10. The [product brief](../PRODUCT.md) defines the audience,
mission, vision and priorities. The work below is planned, not shipped.

## Release 0.4.0

Ship the completed fixes and this agreed product direction. The [changelog](../../CHANGELOG.md)
records what the release changes. A complete round on a real phone and in Safari
remains a release check; automated browser tests do not replace it.

The redesign and keepsakes belong to the next milestone, in this order.

## 1. Comfortable play across devices

Make joining and a complete game comfortable on phones and laptops, both together
and over a voice call.

- Finish a game in portrait without requiring rotation.
- Keep the drawing canvas, toolbar and prompts usable on a phone.
- Keep guessing usable while the software keyboard is open.
- Check joining, drawing, guessing and the reveal on real devices.

### Phone-layout assessment and implementation plan

The portrait assessment found that the stacked drawing layout leaves too little
space for the canvas. Browser measurements gave these results:

| Viewport | Finding |
| --- | --- |
| 320 × 568 px | The drawing canvas has zero height. |
| 390 × 844 px | The drawing canvas is only 202 px tall. |
| 390 × 500 px | During guessing, the drawing frame takes 295 px and the guess panel gets 105 px. The submit control extends below 553 px. |

The shortened 390 × 500 viewport approximates the space left by a software
keyboard. It does not reproduce a real phone's keyboard or Safari's viewport
behaviour. Joining still needs checks with the name field focused, validation
messages visible and the keyboard open.

Implement these changes in the next milestone, in this order:

1. Rebalance `DrawingPhase.svelte` first. Give the mobile canvas panel a minimum
   height that cannot shrink, and override the stage's `min-height: 0` with
   matching selector specificity. Bound the prompt list and let its words scroll.
   Preserve every prompt, check state and the persistent Finish button.
2. In `GuessingPhase.svelte`, constrain the image stage's flex basis and image
   dimensions. Use one scrolling field list and keep Submit outside it. Preserve
   Enter-to-next-field and draft recovery. Add `visualViewport` handling only if
   real-device testing shows CSS cannot keep the focused field visible.
3. Preserve the working joining layout. In `HomeCreateJoin.svelte` and
   `RoomAccessView.svelte`, set room-code capitalization and disable spelling
   correction. Check paste, lowercase normalization, Enter, invalid and full rooms.
   Compact `DrawingToolbar.svelte` only if needed to keep its controls reachable.

Extend `frontend/e2e/mobile-touch.spec.ts` beyond the existing Finish check:

- At 320 × 568 and 390 × 844, keep at least 260 px of drawable canvas, all prompts
  and toolbar controls reachable, and no horizontal overflow.
- Draw with touch without scrolling the canvas; scroll elsewhere and resize
  without losing strokes. Check ten long translated prompts in both themes.
- On real iOS Safari and Android Chrome, enter and edit ten guesses with the
  keyboard open. Keep the focused field and Submit reachable. Dismiss the
  keyboard and reconnect without losing the draft.
- Complete a two-player mixed-device game through reveal without rotation.
  Recheck desktop at 1280 × 720, increased text size and reduced motion.

The measurements used Chromium emulation, synthetic game state, bundled fonts,
a ten-word card and an 800 × 500 drawing. Joining at 320 px and 390 × 500 showed
no horizontal overflow and kept Join visible. Real keyboard and Safari behavior
still need testing. The 2026-11-10 release cut keeps UI implementation outside
0.4.0; the assessment and plan are part of this release.

## 2. Frantic drawing and a shared reveal wall

Use a chaotic sketchbook direction: rough marks, oversized handwriting and playful,
unruly motion. Keep controls predictable, text legible and reduced-motion support.
The drawing phase should feel frantic; the reveal should give friends room to laugh.

Show everyone's drawings together on a shared wall, with a short staggered entrance.
On phones, let players tap a drawing to enlarge it. Preserve the shared view so
friends can compare scribbles and funny guesses together.

## 3. Game-night keepsakes

Extend the existing individual drawing download into one sheet of the shared wall,
including drawings and funny guesses. Let players share or download it to their
device. Start with device export; persistent web links and a server gallery are
outside this milestone.
