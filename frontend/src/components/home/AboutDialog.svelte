<script lang="ts">
import HdDialog from "@/components/ui/HdDialog.svelte";
import { t } from "@/i18n";

let { open = $bindable(false) }: { open?: boolean } = $props();
const attribution = $derived(
  t("home.footerText", {
    original: "{original}",
    inspiration: "{inspiration}",
  }).split(/(\{original\}|\{inspiration\})/),
);
</script>

<HdDialog bind:open title={t("settings.about")} confirmLabel={t("common.confirm")} variant="primary">
  <ul class="about-links">
    <li><a href="https://simonvanlierde.com" target="_blank" rel="noopener">{t("about.madeBy")}</a></li>
    <li><a href="https://github.com/simonvanlierde/6-second-scribbles" target="_blank" rel="noopener">{t("about.source")}</a></li>
    <li><a href="https://github.com/simonvanlierde/6-second-scribbles/blob/main/LICENSE" target="_blank" rel="noopener">{t("about.license")}</a></li>
  </ul>
  <p class="about-text about-credit">
    {#each attribution as part}
      {#if part === "{original}"}
        <a href="https://gamelygames.com/products/six-second-scribbles" target="_blank" rel="noopener">
          Six Second Scribbles
        </a>
      {:else if part === "{inspiration}"}
        <a href="https://github.com/OliverCulleyDeLange/6ss" target="_blank" rel="noopener">
          Oliver Culley de Lange's solo version
        </a>
      {:else}
        {part}
      {/if}
    {/each}
  </p>
  <p class="about-text">{t("home.privacyNote")}</p>
</HdDialog>

<style>
.about-links {
  list-style: none;
  margin: 0 0 20px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.about-links a {
  display: block;
  padding: 12px 16px;
  min-height: 44px;
  box-sizing: border-box;
  font-family: var(--font-body);
  font-size: var(--text-body-lg);
  font-weight: 600;
  color: var(--color-ink);
  text-decoration: none;
  border: 2px solid var(--color-ink);
  border-radius: 14px 18px 12px 16px;
  background: var(--color-card);
}
.about-links a:hover,
.about-links a:focus-visible {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
.about-credit {
  font-size: 0.875rem;
}
.about-text {
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink-muted);
  line-height: 1.6;
  margin: 0 0 20px;
}
.about-text a {
  color: var(--color-ballpoint-blue);
  text-decoration: underline;
}
</style>
