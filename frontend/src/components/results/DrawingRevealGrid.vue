<script setup lang="ts">
import { computed } from "vue";

import DrawingThumbnail from "@/components/results/DrawingThumbnail.vue";
import HdReactionPad from "@/components/ui/HdReactionPad.vue";
import { getAvatarColor } from "@/composables/useAvatar";
import { useGameConnection } from "@/composables/useGameConnection";
import { REACTION_EMOJI, REACTION_KEYS, type ReactionKey, useReactions } from "@/composables/useReactions";
import type { Player } from "@/shared/types";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();
const reactions = useReactions();

const drawings = computed(() => store.playersList.filter((p) => p.drawing));

function colorFor(player: Player): string {
  return player.color ?? getAvatarColor(player.id);
}

function badgesFor(drawingId: string) {
  const counts = reactions.countsFor(drawingId);
  return REACTION_KEYS.filter((key) => counts[key] > 0).map((key) => ({
    key,
    emoji: REACTION_EMOJI[key],
    count: counts[key],
  }));
}

// Server echoes the reaction back to everyone (sender included), so we do not
// optimistically update local counts here — they update on `reaction_received`.
function react(drawingId: string, key: ReactionKey): void {
  send({ type: "reaction_send", drawingId, reactionKey: key });
}
</script>

<template>
  <section class="reveal">
    <h2 class="reveal__title">{{ $t("roundResults.revealTitle") }}</h2>
    <div v-if="drawings.length" class="reveal__grid">
      <div v-for="player in drawings" :key="player.id" class="reveal__cell">
        <DrawingThumbnail
          :drawing="player.drawing"
          :name="player.name"
          :color="colorFor(player)"
          :alt="$t('roundResults.drawingAlt', { name: player.name })"
        >
          <template #overlay>
            <ul v-if="badgesFor(player.id).length" class="reveal__badges">
              <li v-for="badge in badgesFor(player.id)" :key="badge.key" class="reveal__badge">
                <span aria-hidden="true">{{ badge.emoji }}</span>
                <span class="reveal__badge-count">{{ badge.count }}</span>
              </li>
            </ul>
          </template>
        </DrawingThumbnail>
        <HdReactionPad @react="react(player.id, $event)" />
      </div>
    </div>
    <p v-else class="reveal__empty">{{ $t("roundResults.noDrawings") }}</p>
  </section>
</template>

<style scoped>
.reveal__title {
  margin: 0 0 var(--space-3);
  font-size: var(--text-heading-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-ink);
}
.reveal__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-5);
}
.reveal__cell {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  align-items: center;
}
.reveal__badges {
  position: absolute;
  right: var(--space-2);
  bottom: var(--space-2);
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.reveal__badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  font-family: var(--font-body);
  font-size: var(--text-label-sm);
  font-weight: 700;
  color: var(--color-ink);
  background: var(--color-card);
  border: 1.5px solid var(--color-ink);
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-pill);
}
.reveal__empty {
  margin: 0;
  font-family: var(--font-body);
  color: var(--color-ink-muted);
}
@media (max-width: 768px) {
  .reveal__grid {
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-3);
  }
}
</style>
