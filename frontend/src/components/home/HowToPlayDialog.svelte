<script lang="ts">
import HdDialog from "@/components/ui/HdDialog.svelte";
import { t } from "@/i18n";

let { open = $bindable(false) }: { open?: boolean } = $props();
</script>

<HdDialog bind:open title={t("home.howToPlay")} confirmLabel={t("common.gotIt")} variant="primary">
  <ol class="htp">
    <li>{t("home.step1", { count: 10 })}</li>
    <li>{t("home.step2", { time: 60 })}</li>
    <li>{t("home.step3")}</li>
    <li>{t("home.step4")}</li>
  </ol>
</HdDialog>

<style>
.htp {
  margin: 0 0 16px;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  line-height: 1.5;
}
</style>
