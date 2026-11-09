<script lang="ts">
import DrawingThumbnail from "@/components/results/DrawingThumbnail.svelte";
import HdReactionPad from "@/components/ui/HdReactionPad.svelte";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { REACTION_EMOJI, REACTION_KEYS, type ReactionKey, useReactions } from "@/composables/useReactions.svelte";
import { t } from "@/i18n";
import { useGameStore } from "@/stores/game.svelte";

const store = useGameStore();
const { send } = useGameConnection();
const reactions = useReactions();

let drawings = $derived.by(() => store.playersList.filter((p) => p.drawing));

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

<section class="reveal">
  <h2 class="reveal__title">{t("roundResults.revealTitle")}</h2>
  {#if drawings.length}
    <div class="reveal__grid">
      {#each drawings as player (player.id)}
        <div class="reveal__cell">
          <DrawingThumbnail
            drawing={player.drawing}
            name={player.name}
            color={player.color}
            alt={t("roundResults.drawingAlt", { name: player.name })}
          >
            {#if badgesFor(player.id).length}
              <ul class="reveal__badges">
                {#each badgesFor(player.id) as badge (badge.key)}
                  <li class="reveal__badge">
                    <span aria-hidden="true">{badge.emoji}</span>
                    <span class="reveal__badge-count">{badge.count}</span>
                  </li>
                {/each}
              </ul>
            {/if}
          </DrawingThumbnail>
          <HdReactionPad
            name={player.name}
            onreact={(event) => {
              react(player.id, event);
            }}
          ></HdReactionPad>
        </div>
      {/each}
    </div>
  {:else}
    <p class="reveal__empty">{t("roundResults.noDrawings")}</p>
  {/if}
</section>

<style>
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
