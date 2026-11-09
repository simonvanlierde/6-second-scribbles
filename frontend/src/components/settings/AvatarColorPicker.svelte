<script lang="ts">
import HdAvatar from "@/components/ui/HdAvatar.svelte";
import { AVATAR_COLOR_NAMES, AVATAR_COLORS, type AvatarColor } from "@/composables/useAvatar";
import { t } from "@/i18n";

let {
  initial,
  modelValue: model = $bindable(),
  onmodelValueChange,
}: { initial: string } & { modelValue: AvatarColor; onmodelValueChange?: (value: AvatarColor) => void } = $props();
</script>

<div class="avatar-picker" role="radiogroup" aria-label={t("settings.avatarColor")}>
  {#each AVATAR_COLORS as c (c)}<!-- biome-ignore lint/a11y/useSemanticElements: color swatches retain button activation within the named selection group. -->
    <button
      class={["avatar-picker__btn", { "avatar-picker__btn--active": c === model }]}
      type="button"
      aria-label={t(AVATAR_COLOR_NAMES[c])}
      role="radio"
      aria-checked={c === model}
      onclick={() => {
        model = c;
        onmodelValueChange?.(c);
      }}
    >
      <HdAvatar {initial} color={c} size="md"></HdAvatar>
    </button>
  {/each}
</div>

<style>
.avatar-picker {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.avatar-picker__btn {
  background: transparent;
  border: 0;
  padding: 4px;
  border-radius: 14px;
  cursor: pointer;
  transition: transform var(--motion-fast) var(--ease-spring);
}
/* A fill, not an outline: the blue outline is the keyboard focus ring. */
.avatar-picker__btn--active {
  background: var(--color-highlighter-yellow);
  box-shadow: inset 0 0 0 2px var(--color-ink);
}
.avatar-picker__btn:active {
  transform: scale(0.94);
}
</style>
