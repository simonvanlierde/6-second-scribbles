<script lang="ts">
import HdDialog from "@/components/ui/HdDialog.svelte";
import { t } from "@/i18n";

let { open = $bindable(false) }: { open?: boolean } = $props();
const attribution = $derived(
  t("home.footerText", {
    original: "{original}",
    inspiration: "{inspiration}",
    source: "{source}",
  }).split(/(\{original\}|\{inspiration\}|\{source\})/),
);
</script>

<HdDialog bind:open title={t("settings.about")} confirmLabel={t("common.confirm")} variant="primary">
  <p class="about-text">
    {#each attribution as part}
      {#if part === "{original}"}
        <a href="https://gamelygames.com/products/six-second-scribbles" target="_blank" rel="noopener">
          Six Second Scribbles
        </a>
      {:else if part === "{inspiration}"}
        <a href="https://github.com/OliverCulleyDeLange/6ss" target="_blank" rel="noopener">
          Oliver Culley de Lange's solo version
        </a>
      {:else if part === "{source}"}
        <a href="https://github.com/simonvanlierde/6-second-scribbles" target="_blank" rel="noopener">
          Source on GitHub
        </a>
      {:else}
        {part}
      {/if}
    {/each}
  </p>
  <p class="about-text">{t("home.privacyNote")}</p>
</HdDialog>

<style>
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
