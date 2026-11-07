<script lang="ts">
import { onMount, tick } from "svelte";
import GameHeader from "@/components/game/GameHeader.svelte";
import LeaveRoomDialog from "@/components/LeaveRoomDialog.svelte";
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import HdButton from "@/components/ui/HdButton.svelte";
import HdCard from "@/components/ui/HdCard.svelte";
import HdDialog from "@/components/ui/HdDialog.svelte";
import HdInput from "@/components/ui/HdInput.svelte";
import HdPill from "@/components/ui/HdPill.svelte";
import { getAvatarInitial } from "@/composables/useAvatar";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { useGameTimer } from "@/composables/useGameTimer.svelte";
import { useRoundDraft } from "@/composables/useRoundDraft";
import { useSound } from "@/composables/useSound.svelte";
import { STORAGE_KEYS } from "@/config/gameConfig";
import { t } from "@/i18n";
import { useGameStore } from "@/stores/game.svelte";

const store = useGameStore();
const { send } = useGameConnection();
const { play } = useSound();

let playerGuesses = $state<Record<string, string[]>>({});
let submittedPlayers = $state<string[]>([]);
let allGuessesSubmitted = $state(false);
let leaveDialog = $state<ReturnType<typeof LeaveRoomDialog> | null>(null);
let guessPanel = $state<HTMLElement | null>(null);
let skipDialogOpen = $state(false);
let emptyGuessDialogTarget = $state<string | null>(null);

let assignedTargetPlayerId = $derived.by(() => store.guessTargets[store.localPlayerId] || null);
let assignedTargetPlayer = $derived.by(() =>
  assignedTargetPlayerId ? store.playersList.find((p) => p.id === assignedTargetPlayerId) || null : null,
);
let brokenImages = $state<Set<string>>(new Set());

const timer = useGameTimer({
  startTime: () => store.guessingStartTime,
  duration: () => store.guessingTimeLimit,
  onExpire: () => autoSubmitGuesses(),
});

// Typed guesses are client-only until submitted, so they're drafted locally and
// restored on reconnect — mirroring the drawing-phase stroke recovery.
const draft = useRoundDraft<Record<string, string[]>>(STORAGE_KEYS.GUESSING_STATE, {
  round: () => store.currentRound,
  collect: () => playerGuesses,
  apply: (data) => {
    playerGuesses = data;
  },
  active: () => !allGuessesSubmitted,
});

// Ensure the assigned target always has at least one (empty) guess field.
// Seeding here (not lazily inside the template) keeps guessesFor a pure read,
// so rendering never mutates reactive state.
function ensureAssignedGuess() {
  const target = assignedTargetPlayerId;
  if (target && !playerGuesses[target]) playerGuesses[target] = [""];
}

// Seed synchronously so the first render already shows an input.
ensureAssignedGuess();

onMount(() => {
  submittedPlayers = [];
  draft.restore();
  ensureAssignedGuess();
});

function guessesFor(playerId: string): string[] {
  return playerGuesses[playerId] ?? [];
}

function onGuessInput(playerId: string, idx: number) {
  const guesses = playerGuesses[playerId] || [];
  if (idx === guesses.length - 1 && guesses[idx]?.trim() !== "" && guesses.length < 10) {
    playerGuesses[playerId] = [...guesses, ""];
  }
}

function handleGuessKeydown(playerId: string, idx: number, event: KeyboardEvent) {
  if (event.key !== "Enter") return;
  event.preventDefault();
  onGuessInput(playerId, idx);
  tick().then(() => {
    const inputs = document.querySelectorAll<HTMLInputElement>(".guess-input");
    inputs[idx + 1]?.focus();
  });
}

function autoSubmitGuesses() {
  if (!assignedTargetPlayerId) return;
  const targetId = assignedTargetPlayerId;
  if (!submittedPlayers.includes(targetId)) {
    const guesses = (playerGuesses[targetId] || []).filter((g) => g.trim() !== "");
    doSubmitGuesses(targetId, guesses);
  }
}

function submitGuessesForPlayer(targetPlayerId: string) {
  play("click");
  const guesses = (playerGuesses[targetPlayerId] || []).filter((g) => g.trim() !== "");
  if (guesses.length === 0) {
    emptyGuessDialogTarget = targetPlayerId;
    skipDialogOpen = true;
    return;
  }
  doSubmitGuesses(targetPlayerId, guesses);
}

function confirmSkipGuesses() {
  const targetPlayerId = emptyGuessDialogTarget;
  emptyGuessDialogTarget = null;
  if (targetPlayerId) doSubmitGuesses(targetPlayerId, []);
}

function cancelSkipGuesses() {
  emptyGuessDialogTarget = null;
}

function doSubmitGuesses(targetPlayerId: string, guesses: string[]) {
  send({ type: "submit_guess", playerId: store.localPlayerId, targetPlayerId, guesses });
  if (!submittedPlayers.includes(targetPlayerId)) {
    submittedPlayers = [...submittedPlayers, targetPlayerId];
  }

  if (assignedTargetPlayerId && submittedPlayers.includes(assignedTargetPlayerId)) {
    allGuessesSubmitted = true;
    send({ type: "player_ready", playerId: store.localPlayerId });
    draft.clear();
    // The submit button goes away with the form; keep focus in place instead of on <body>.
    void tick().then(() => guessPanel?.focus());
  }
}

function handleImageError(playerId: string) {
  brokenImages = new Set([...brokenImages, playerId]);
}
</script>

<main class="guessing-phase">
  <GameHeader
    timeLeft={timer.timeLeft}
    title={t("phase.guessing", { round: store.currentRound })}
    onleave={() => {
      leaveDialog?.request();
    }}
  ></GameHeader>

  <div class="guessing-phase__body">
    {#if assignedTargetPlayer}
      <!-- Drawing frame -->
      <HdCard class="drawing-frame">
        <h2 class="drawing-frame__title">
          <HdAvatar
            initial={getAvatarInitial(assignedTargetPlayer.name)}
            color={assignedTargetPlayer.color}
            size="sm"
            disconnected={!assignedTargetPlayer.connected}
          ></HdAvatar>
          {t("guessing.guessPlayerDrawing", { name: assignedTargetPlayer.name })}
        </h2>
        <div class="drawing-frame__stage">
          {#if assignedTargetPlayer.drawing && !brokenImages.has(assignedTargetPlayer.id)}
            <!-- biome-ignore lint/a11y/noNoninteractiveElementInteractions: onerror handles image resource failures. -->
            <img
              class="drawing-frame__img"
              src={assignedTargetPlayer.drawing}
              alt={t("guessing.playerDrawingAlt")}
              onerror={() => {
                handleImageError(assignedTargetPlayer.id);
              }}
            >
          {:else if brokenImages.has(assignedTargetPlayer.id)}
            <p class="drawing-frame__placeholder">
              {t("guessing.drawingFailed")}
            </p>
          {:else}
            <p class="drawing-frame__placeholder">{t("guessing.waitingForDrawing")}</p>
          {/if}
        </div>
      </HdCard>

      <!-- Guess panel. It scrolls, so once submitted (nothing inside takes focus)
             it takes focus itself, letting keyboard users scroll it. -->
      <!-- svelte-ignore a11y_no_noninteractive_tabindex (The submitted panel takes focus so keyboard users can scroll.) -->
      <section
        class="guess-panel"
        bind:this={guessPanel}
        aria-label={t("guessing.yourGuesses")}
        tabindex={submittedPlayers.includes(assignedTargetPlayer.id) ? 0 : undefined}
      >
        {#if submittedPlayers.includes(assignedTargetPlayer.id)}
          <HdCard class="guess-submitted" variant="postit">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            {t("guessing.submittedWaiting")}
          </HdCard>
        {:else}
          <HdCard class="guess-card">
            <div class="guess-card__header">
              <h3 class="guess-card__title">{t("guessing.yourGuesses")}</h3>
              <HdPill variant="info">
                {guessesFor(assignedTargetPlayer.id).filter((g) => g.trim()).length}
                / 10
              </HdPill>
            </div>
            <div class="guess-card__grid">
              {#each guessesFor(assignedTargetPlayer.id) as _, idx (idx)}
                <HdInput
                  class="guess-input"
                  bind:modelValue={playerGuesses[assignedTargetPlayer.id][idx]}
                  placeholder={t("guessing.guessNumber", { number: idx + 1 })}
                  ariaLabel={t("guessing.guessNumber", { number: idx + 1 })}
                  oninput={() => {
                    onGuessInput(assignedTargetPlayer.id, idx);
                  }}
                  onkeydown={(event) => {
                    handleGuessKeydown(assignedTargetPlayer.id, idx, event);
                  }}
                ></HdInput>
              {/each}
            </div>
            <HdButton
              class="guess-card__submit"
              variant="primary"
              onclick={() => {
                submitGuessesForPlayer(assignedTargetPlayer.id);
              }}
            >
              {t("guessing.submitGuesses")}
            </HdButton>
          </HdCard>
          <HdCard class="guess-hint" variant="postit">{t("guessing.hint")}</HdCard>
        {/if}
      </section>
    {:else}
      <div class="guessing-phase__waiting">
        <p>{t("guessing.waitingForAssignedDrawing")}</p>
      </div>
    {/if}
  </div>

  <LeaveRoomDialog bind:this={leaveDialog}></LeaveRoomDialog>

  <HdDialog
    bind:open={skipDialogOpen}
    title={t("guessing.noGuessesTitle")}
    message={t("guessing.noGuessesMessage")}
    confirmLabel={t("guessing.submitAnyway")}
    cancelLabel={t("guessing.goBack")}
    variant="primary"
    onconfirm={confirmSkipGuesses}
    oncancel={cancelSkipGuesses}
  ></HdDialog>
</main>

<style>
.guessing-phase {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  width: 100%;
  overflow: hidden;
  background: var(--color-paper);
}
.guessing-phase__body {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: var(--space-4);
  padding: var(--space-4);
  overflow: hidden;
}

/* Drawing frame */
:global(div.hd-card.drawing-frame) {
  display: flex;
  flex-direction: column;
  flex: 1.2;
  min-width: 0;
  min-height: 0;
}
.drawing-frame__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 2.5px solid var(--color-marker-red);
  font-size: var(--text-heading-sm);
}
.drawing-frame__stage {
  display: flex;
  flex: 1;
  min-height: 0;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: var(--r-input);
  background: var(--color-paper);
}
.drawing-frame__img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.drawing-frame__placeholder {
  font-style: italic;
  color: var(--color-ink-muted);
}

/* Guess panel */
.guess-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
}
:global(div.hd-card.guess-card) {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.guess-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.guess-card__title {
  margin: 0;
  font-size: var(--text-heading-sm);
}
.guess-card__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}
:global(button.hd-btn.guess-card__submit) {
  width: 100%;
}
:global(div.hd-card.guess-submitted) {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 700;
}
:global(div.hd-card.guess-submitted) svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}
:global(div.hd-card.guess-hint) {
  font-size: var(--text-label-md);
}
.guessing-phase__waiting {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: center;
  font-style: italic;
  color: var(--color-ink-muted);
}

@media (max-width: 768px) {
  .guessing-phase__body {
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-3);
    overflow-y: auto;
  }
  :global(div.hd-card.drawing-frame) {
    flex: none;
  }
  .drawing-frame__stage {
    height: min(155px, 26dvh);
  }
  .guess-card__grid {
    grid-template-columns: 1fr;
  }
}
</style>
