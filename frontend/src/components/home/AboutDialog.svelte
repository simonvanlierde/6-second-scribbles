<script lang="ts">
import HdDialog from "@/components/ui/HdDialog.svelte";
import { t } from "@/i18n";

let { open = $bindable(false) }: { open?: boolean } = $props();
</script>

<HdDialog bind:open title={t("settings.about")} confirmLabel={t("common.confirm")} variant="primary">
  <p class="about-text">
    <i18n-t keypath="home.footerText" tag="span">
      <a href="https://gamelygames.com/products/six-second-scribbles" target="_blank" rel="noopener">
        Six Second Scribbles
      </a>

      <a href="https://github.com/OliverCulleyDeLange/6ss" target="_blank" rel="noopener">
        Oliver Culley de Lange's solo version
      </a>

      <a href="https://github.com/simonvanlierde/6-second-scribbles" target="_blank" rel="noopener">
        Source on GitHub
      </a>
    </i18n-t>
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
