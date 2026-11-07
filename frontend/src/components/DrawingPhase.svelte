<script lang="ts">
import { onDestroy, onMount, untrack } from "svelte";
import DrawingCanvasStage from "@/components/DrawingCanvasStage.svelte";
import DrawingToolbar from "@/components/DrawingToolbar.svelte";
import GameHeader from "@/components/game/GameHeader.svelte";
import LeaveRoomDialog from "@/components/LeaveRoomDialog.svelte";
import HdButton from "@/components/ui/HdButton.svelte";
import HdCard from "@/components/ui/HdCard.svelte";
import { useDrawingCanvas } from "@/composables/useDrawingCanvas.svelte";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { useGameTimer } from "@/composables/useGameTimer.svelte";
import { useRoundDraft } from "@/composables/useRoundDraft";
import { useSound } from "@/composables/useSound.svelte";
import { BRUSH_SIZES, DRAW_PALETTE, DRAWING_PAPER } from "@/config/drawing";
import { STORAGE_KEYS } from "@/config/gameConfig";
import { t } from "@/i18n";
import { encodeDrawing } from "@/lib/drawingImage";
import { useGameStore } from "@/stores/game.svelte";

const store = useGameStore();
const { send } = useGameConnection();
const { play } = useSound();
const canvas = useDrawingCanvas();

let canvasElement = $state<HTMLCanvasElement | null>(null);
let hasSubmittedDrawing = $state(false);
let leaveDialog = $state<ReturnType<typeof LeaveRoomDialog> | null>(null);
let doneItems = $state<Set<number>>(new Set());

let category = $derived.by(() => store.localPlayerCard?.category || t("drawing.loadingCategory"));
let items = $derived.by(() => store.localPlayerCard?.items || []);

const timer = useGameTimer({
  startTime: () => store.roundStartTime,
  duration: () => store.drawingTimeLimit,
  onExpire: () => endDrawingPhase(),
});

// Last-10-seconds tick.
let watchStarted0 = false;
$effect(() => {
  const value = timer.timeLeft;
  if (!watchStarted0) {
    watchStarted0 = true;
    return;
  }
  untrack(() => {
    const left = value;
    if (left > 0 && left <= 10) play("tick");
  });
});

// In-progress strokes are the one piece of drawing state the server doesn't hold
// until submit, so they're drafted locally and restored on reconnect. The card
// is restored from the authoritative room_state snapshot (see applyRoomState);
// the saved copy here is only a pre-snapshot fallback.
const draft = useRoundDraft<{ localPlayerCard: typeof store.localPlayerCard; strokes: typeof canvas.strokes }>(
  STORAGE_KEYS.DRAWING_STATE,
  {
    round: () => store.currentRound,
    collect: () => ({ localPlayerCard: store.localPlayerCard, strokes: canvas.strokes }),
    apply: (data) => {
      if (!store.localPlayerCard && data.localPlayerCard) store.localPlayerCard = data.localPlayerCard;
      if (data.strokes) canvas.replaceStrokes(data.strokes);
    },
    active: () => !hasSubmittedDrawing,
  },
);

onMount(() => {
  play("roundStart");
  canvas.setColor(DRAW_PALETTE[0]);
  canvas.setWidth(BRUSH_SIZES[1]);

  if (canvasElement) {
    canvas.initCanvas(canvasElement);
    draft.restore();
  }
});

onDestroy(() => canvas.cleanup());

export function endDrawingPhase() {
  if (hasSubmittedDrawing) return;
  hasSubmittedDrawing = true;
  // Keep the timer running: it shows the shared round countdown, which still
  // ticks for everyone else after this player submits early.

  const el = canvas.canvasRef;
  const drawing = el && encodeDrawing(el, DRAWING_PAPER);
  if (drawing) {
    send({ type: "draw_stroke", playerId: store.localPlayerId, drawing });
    // Keep our own copy too — the receive handler skips own-player strokes, so
    // without this the end-of-game gallery would miss this player's drawing.
    store.setPlayerDrawing(store.localPlayerId, drawing);
  }

  send({ type: "player_ready", playerId: store.localPlayerId });
  draft.clear();
}

function finishDrawing() {
  play("click");
  endDrawingPhase();
}

function toggleItem(index: number) {
  const next = new Set(doneItems);
  if (next.has(index)) next.delete(index);
  else next.add(index);
  doneItems = next;
}
</script>

<main class="drawing-phase">
  <GameHeader
    timeLeft={timer.timeLeft}
    title={t("phase.drawing", { round: store.currentRound })}
    onleave={() => {
      leaveDialog?.request();
    }}
  ></GameHeader>

  <div class="drawing-phase__body">
    <!-- Category sidebar -->
    <aside class="drawing-phase__sidebar">
      <!-- Above the list: below it, the sticky Finish button covers it on short screens. -->
      <HdCard class="drawing-phase__hint" variant="postit">{t("drawing.hint")}</HdCard>

      <HdCard class="category-card">
        <h2 class="category-card__title">{category}</h2>
        <ol class="category-card__list">
          {#each items as item, index (index)}
            <li>
              <button
                class={["category-card__item", { "category-card__item--done": doneItems.has(index) }]}
                type="button"
                aria-pressed={doneItems.has(index)}
                onclick={() => {
                  toggleItem(index);
                }}
              >
                <span class="category-card__num">{index + 1}</span>
                <span class="category-card__text">{item}</span>
              </button>
            </li>
          {/each}
        </ol>
      </HdCard>

      <HdButton
        class="drawing-phase__finish-desktop"
        variant="success"
        disabled={hasSubmittedDrawing}
        onclick={finishDrawing}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        {hasSubmittedDrawing ? t("drawing.waiting") : t("drawing.finish")}
      </HdButton>
    </aside>

    <!-- Canvas panel -->
    <div class="drawing-phase__canvas-panel">
      <DrawingToolbar
        currentColor={canvas.currentColor}
        currentWidth={canvas.currentWidth}
        onselectColor={canvas.setColor}
        onselectSize={canvas.setWidth}
        onundo={() => {
          canvas.undo();
        }}
        onclear={() => {
          canvas.clear();
        }}
      ></DrawingToolbar>

      <DrawingCanvasStage class="drawing-phase__stage"><canvas bind:this={canvasElement}></canvas></DrawingCanvasStage>
    </div>
  </div>

  <!-- Outside the scrolling body, so it stays on screen however tall the card is. -->
  <HdButton
    class="drawing-phase__finish-mobile"
    variant="success"
    disabled={hasSubmittedDrawing}
    onclick={finishDrawing}
  >
    {hasSubmittedDrawing ? t("drawing.waiting") : t("drawing.finish")}
  </HdButton>

  <LeaveRoomDialog bind:this={leaveDialog}></LeaveRoomDialog>
</main>

<style>
.drawing-phase {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  width: 100%;
  overflow: hidden;
  background: var(--color-paper);
}
.drawing-phase__body {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: var(--space-4);
  padding: var(--space-4);
  overflow: hidden;
}
.drawing-phase__sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 240px;
  flex-shrink: 0;
  overflow-y: auto;
  /* Room for the card and button shadows, which the scroll box would clip. */
  padding: 0 4px 4px 0;
}
.category-card__title {
  margin: 0 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 2.5px solid var(--color-marker-red);
  font-size: var(--text-heading-sm);
}
.category-card__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.category-card__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  background: transparent;
  border: 0;
  padding: 6px 4px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  cursor: pointer;
  text-align: left;
  border-radius: 6px;
  min-height: 44px;
}
.category-card__item:hover {
  background: color-mix(in srgb, var(--color-ink) 6%, transparent);
}
.category-card__num {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-label-sm);
  border: 1.5px solid var(--color-ink);
  border-radius: var(--r-pill);
}
.category-card__item--done .category-card__text {
  text-decoration: line-through wavy var(--color-marker-red);
  color: var(--color-ink-muted);
}
.category-card__item--done .category-card__num {
  background: var(--color-meadow-green);
  color: var(--color-ink-fixed);
}
:global(div.hd-card.drawing-phase__hint) {
  font-size: var(--text-label-md);
}
/* On a short laptop screen (1280x720) a ten-word card, the hint and Finish only fit
 * with shorter rows. 32px is still above the 24px minimum target size. */
@media (min-width: 769px) and (max-height: 800px) {
  .category-card__item {
    min-height: 32px;
    padding-block: 2px;
  }
}
/* Sticky, so a word card taller than the window cannot push it out of the scrolling sidebar. */
:global(button.hd-btn.drawing-phase__finish-desktop) {
  position: sticky;
  bottom: 4px;
  flex-shrink: 0;
  margin-top: auto;
}
:global(button.hd-btn.drawing-phase__finish-desktop) svg {
  width: 20px;
  height: 20px;
}
:global(button.hd-btn.drawing-phase__finish-mobile) {
  display: none;
}

.drawing-phase__canvas-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  min-height: 0;
  gap: var(--space-3);
}
:global(div.canvas-stage.drawing-phase__stage) {
  flex: 1;
  min-height: 0;
}

@media (max-width: 768px) {
  .drawing-phase__body {
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-3);
    overflow-y: auto;
  }
  .drawing-phase__sidebar {
    width: auto;
    flex-shrink: 0;
    overflow-y: visible;
  }
  /* Two columns (column-major: 1–5 left, 6–10 right) to reclaim vertical space. */
  .category-card__list {
    display: block;
    columns: 2;
    column-gap: var(--space-5);
  }
  .category-card__list li {
    break-inside: avoid;
    margin-bottom: var(--space-1);
  }
  /* Phones keep the shorter rows, so the canvas keeps the vertical space. */
  .category-card__item {
    min-height: auto;
    font-size: var(--text-body-lg);
  }
  :global(button.hd-btn.drawing-phase__finish-desktop) {
    display: none;
  }
  :global(button.hd-btn.drawing-phase__finish-mobile) {
    display: inline-flex;
    flex-shrink: 0;
    margin: 0 var(--space-3) calc(var(--space-3) + env(safe-area-inset-bottom));
  }
  :global(.canvas-stage) {
    min-height: 260px;
  }
}
</style>
