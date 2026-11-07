<script lang="ts">
import DrawingThumbnail from "@/components/results/DrawingThumbnail.svelte";
import HdIconButton from "@/components/ui/HdIconButton.svelte";
import { useDrawingExport } from "@/composables/useDrawingExport";
import { t } from "@/i18n";
import type { GalleryDrawing } from "@/shared/types";

let { drawings }: { drawings: GalleryDrawing[] } = $props();

const { exportDrawing } = useDrawingExport();

function slug(value: string): string {
  return (
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "drawing"
  );
}

function download(d: GalleryDrawing): void {
  exportDrawing(d.drawing, `scribble-${slug(d.name)}-r${d.round}.png`);
}
</script>

<section class="gallery">
  <h2 class="gallery__title">{t("finalResults.allDrawings")}</h2>
  {#if drawings.length}
    <div class="gallery__grid">
      {#each drawings as d (`${d.playerId}-${d.round}`)}
        <div class="gallery__cell">
          <DrawingThumbnail
            drawing={d.drawing}
            name={d.name}
            color={d.color}
            alt={t("roundResults.drawingAlt", { name: d.name })}
          >
            <HdIconButton
              class="gallery__download"
              label={t("finalResults.downloadDrawing", { name: d.name })}
              onclick={() => {
                download(d);
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
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </HdIconButton>
          </DrawingThumbnail>
          <span class="gallery__tag">{t("finalResults.roundTag", { round: d.round })}</span>
        </div>
      {/each}
    </div>
  {:else}
    <p class="gallery__empty">{t("roundResults.noDrawings")}</p>
  {/if}
</section>

<style>
.gallery__title {
  margin: 0 0 var(--space-3);
  font-size: var(--text-heading-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-ink);
}
.gallery__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-5);
}
.gallery__cell {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  align-items: center;
}
.gallery__tag {
  font-family: var(--font-body);
  font-size: var(--text-label-sm);
  color: var(--color-ink-muted);
}
/* Download affordance: hidden until hover/focus on pointer devices, always
 * visible on touch. Reveal uses opacity (no transform) so reduced-motion is fine. */
:global(button.hd-icon-btn.gallery__download) {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  opacity: 0;
  transition: opacity var(--motion-fast) var(--ease-out);
}
.gallery__cell:hover :global(button.hd-icon-btn.gallery__download),
.gallery__cell:focus-within :global(button.hd-icon-btn.gallery__download) {
  opacity: 1;
}
@media (hover: none) {
  :global(button.hd-icon-btn.gallery__download) {
    opacity: 1;
  }
}
.gallery__empty {
  margin: 0;
  font-family: var(--font-body);
  color: var(--color-ink-muted);
}
@media (max-width: 768px) {
  .gallery__grid {
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-3);
  }
}
</style>
