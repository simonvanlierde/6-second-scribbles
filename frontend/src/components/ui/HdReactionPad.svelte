<script lang="ts">
import type { HTMLAttributes } from "svelte/elements";
import { REACTION_EMOJI, REACTION_KEYS, type ReactionKey } from "@/composables/useReactions.svelte";
import { t } from "@/i18n";

let {
  name,
  onreact,
  ...rest
}: { name: string } & { onreact?: (reaction: ReactionKey) => void } & HTMLAttributes<HTMLElement> = $props();

const LABEL_KEYS: Record<ReactionKey, string> = {
  laugh: "reactions.laugh",
  shock: "reactions.shock",
  art: "reactions.art",
  "mind-blown": "reactions.mindBlown",
  think: "reactions.think",
};
</script>

<!-- biome-ignore lint/a11y/useSemanticElements: role=group + aria-label names the reaction button cluster; no native element fits -->
<div {...rest} class={[rest.class, "hd-rpad"]} role="group" aria-label={t("reactions.group", { name })}>
  {#each REACTION_KEYS as k (k)}
    <button
      class="hd-rpad__btn"
      type="button"
      aria-label={t("reactions.react", { reaction: t(LABEL_KEYS[k]), name })}
      onclick={() => {
        onreact?.(k);
      }}
    >
      {REACTION_EMOJI[k]}
    </button>
  {/each}
</div>

<style>
.hd-rpad {
  display: inline-flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: center;
}
.hd-rpad__btn {
  width: 44px;
  height: 44px;
  border-radius: 12px 16px 11px 14px;
  background: var(--color-card);
  border: 2px solid var(--color-ink);
  box-shadow: 2px 2px 0 var(--color-ink);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  cursor: pointer;
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring);
}
.hd-rpad__btn:active {
  transform: translate(2px, 2px);
  box-shadow: 0 0 0 var(--color-ink);
}
</style>
