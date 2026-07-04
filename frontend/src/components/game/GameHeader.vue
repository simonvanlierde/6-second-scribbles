<script setup lang="ts">
import { computed } from "vue";

import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdIconButton from "@/components/ui/HdIconButton.vue";
import HdTimer from "@/components/ui/HdTimer.vue";
import { getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { useSound } from "@/composables/useSound";
import { useGameStore } from "@/stores/game";

withDefaults(
  defineProps<{
    /** Countdown shown in the timer; ignored in "final" mode. */
    timeLeft?: number;
    /** "game" shows the timer + round/score; "final" shows a title + status chip. */
    variant?: "game" | "final";
    /** Title shown in "final" mode (e.g. "Game over"). */
    title?: string;
    /** Status chip text shown in "final" mode (e.g. a result summary). */
    status?: string;
  }>(),
  { timeLeft: 0, variant: "game", title: "", status: "" },
);
defineEmits<{ leave: [] }>();

const store = useGameStore();
const { enabled: soundEnabled } = useSound();

const score = computed(() => store.localPlayer?.score ?? 0);
const initial = computed(() => getAvatarInitial(store.localPlayerName || "?"));
const avatarColor = computed(() => store.localPlayerColor ?? getAvatarColor(store.localPlayerId));
</script>

<template>
  <header class="game-header">
    <div class="game-header__cluster">
      <HdIconButton :label="$t('common.leave')" @click="$emit('leave')">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </HdIconButton>
      <HdIconButton
        :label="soundEnabled ? $t('common.soundMute') : $t('common.soundUnmute')"
        :aria-pressed="soundEnabled"
        @click="soundEnabled = !soundEnabled"
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
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
          <template v-if="soundEnabled">
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
          </template>
          <template v-else>
            <line x1="23" y1="9" x2="17" y2="15" />
            <line x1="17" y1="9" x2="23" y2="15" />
          </template>
        </svg>
      </HdIconButton>
    </div>

    <template v-if="variant === 'final'">
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
          <path d="M4 22V4s1.5-1 5-1 5 2 8.5 2 3.5-1 3.5-1v11s-1 1-3.5 1-5-2-8.5-2-5 1-5 1" />
        </svg>
        {{ title }}
      </h1>
      <div class="game-header__meta"><span v-if="status" class="game-header__status">{{ status }}</span></div>
      <HdAvatar class="game-header__avatar" :initial="initial" :color="avatarColor" size="sm" />
    </template>

    <template v-else>
      <div class="game-header__timer"><HdTimer :seconds="timeLeft" /></div>

      <div class="game-header__meta">
        <span class="game-header__round">
          {{ $t("common.roundProgress", { current: store.currentRound, total: store.maxRounds }) }}
          <span v-if="store.readyCount > 0" class="game-header__ready">
            · {{ store.readyCount }}/{{ store.totalPlayers }}
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
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </span>
        </span>
        <span class="game-header__score">{{ $t("common.pointsShort", { count: score }) }}</span>
      </div>
      <HdAvatar class="game-header__avatar" :initial="initial" :color="avatarColor" size="sm" />
    </template>
  </header>
</template>

<style scoped>
.game-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
  background: var(--color-ink);
  color: var(--color-paper);
  border-bottom: 2.5px solid var(--color-ink);
  padding: var(--space-2) var(--space-4);
  /* Reserve space at the right for the global settings gear (fixed, top-right). */
  padding-right: calc(var(--space-4) + 52px);
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
.game-header__status {
  font-size: var(--text-label-md);
  font-weight: 700;
  text-align: right;
  white-space: nowrap;
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
  width: 13px;
  height: 13px;
  vertical-align: -1px;
}
.game-header__score {
  font-size: var(--text-label-sm);
  opacity: 0.75;
  white-space: nowrap;
}
.game-header__avatar {
  flex-shrink: 0;
}
@media (max-width: 768px) {
  .game-header {
    gap: var(--space-2);
    padding: var(--space-1) var(--space-3);
    padding-right: calc(var(--space-3) + 48px);
  }
  .game-header__avatar {
    display: none;
  }
}
</style>
