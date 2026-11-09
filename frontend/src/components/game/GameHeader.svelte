<script lang="ts">
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import HdIconButton from "@/components/ui/HdIconButton.svelte";
import HdTimer from "@/components/ui/HdTimer.svelte";
import { getAvatarInitial } from "@/composables/useAvatar";
import { useSound } from "@/composables/useSound.svelte";
import { t } from "@/i18n";
import { useGameStore } from "@/stores/game.svelte";

let {
  timeLeft = 0,
  variant = "game",
  title = "",
  onleave,
}: {
  timeLeft?: number;

  variant?: "game" | "final";

  title?: string;
} & { onleave?: () => void } = $props();

const store = useGameStore();
const sound = useSound();

let score = $derived.by(() => store.localPlayer?.score ?? 0);
let initial = $derived.by(() => getAvatarInitial(store.localPlayerName || "?"));
let avatarColor = $derived.by(() => store.localAvatarColor);
</script>

<header class="game-header">
  <div class="game-header__cluster">
    <HdIconButton
      label={t("common.leave")}
      onclick={() => {
        onleave?.();
      }}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <polyline points="15 18 9 12 15 6"></polyline>
      </svg>
    </HdIconButton>
    <HdIconButton
      label={sound.enabled ? t("common.soundMute") : t("common.soundUnmute")}
      aria-pressed={sound.enabled}
      onclick={() => {
        sound.enabled = !sound.enabled;
      }}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
        {#if sound.enabled}
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
        {:else}
          <line x1="23" y1="9" x2="17" y2="15"></line>
          <line x1="17" y1="9" x2="23" y2="15"></line>
        {/if}
      </svg>
    </HdIconButton>
  </div>

  {#if variant === "final"}
    <h1 class="game-header__title">
      <svg
        class="game-header__flag"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M4 22V4s1.5-1 5-1 5 2 8.5 2 3.5-1 3.5-1v11s-1 1-3.5 1-5-2-8.5-2-5 1-5 1"></path>
      </svg>
      {title}
    </h1>
    <div class="game-header__meta"></div>
    <HdAvatar class="game-header__avatar" {initial} color={avatarColor} size="sm"></HdAvatar>
  {:else}
    {#if title}
      <h1 class="sr-only">{title}</h1>
    {/if}
    <div class="game-header__timer"><HdTimer seconds={timeLeft}></HdTimer></div>

    <div class="game-header__meta">
      <span class="game-header__round">
        {t("common.roundProgress", { current: store.currentRound, total: store.maxRounds })}
        {#if store.readyCount > 0}
          <span class="game-header__ready">
            · {store.readyCount}/{store.totalPlayers}
            <svg
              class="game-header__check"
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
          </span>
        {/if}</span
      >
      <span class="game-header__score">{t("common.pointsShort", { count: score })}</span>
    </div>
    <HdAvatar class="game-header__avatar" {initial} color={avatarColor} size="sm"></HdAvatar>
  {/if}
</header>

<style>
.game-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
  background: var(--color-ink);
  color: var(--color-paper);
  border-bottom: 2.5px solid var(--color-ink);
  padding: var(--space-2) var(--space-4);
  /* Reserve space at the right for the global settings gear: the app fixes it
   * 44px wide at max(20px, safe-area) from the right edge. */
  padding-right: calc(max(20px, env(safe-area-inset-right)) + 44px + var(--space-2));
}
.game-header__cluster {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex: 1;
}
.game-header__timer {
  flex-shrink: 0;
}
.game-header__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  flex-shrink: 0;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  white-space: nowrap;
}
.game-header__flag {
  width: 22px;
  height: 22px;
}
.game-header__meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex: 1;
  min-width: 0;
}
.game-header__round {
  font-size: var(--text-label-md);
  font-weight: 700;
  white-space: nowrap;
}
.game-header__ready {
  font-weight: 400;
  opacity: 0.65;
}
.game-header__check {
  display: inline-block;
  width: 13px;
  height: 13px;
  vertical-align: -1px;
}
.game-header__score {
  font-size: var(--text-label-sm);
  opacity: 0.75;
  white-space: nowrap;
}
:global(span.hd-avatar.game-header__avatar) {
  flex-shrink: 0;
}
@media (max-width: 768px) {
  .game-header {
    gap: var(--space-2);
    padding-block: var(--space-1);
    padding-left: var(--space-3);
  }
  :global(span.hd-avatar.game-header__avatar) {
    display: none;
  }
}
</style>
