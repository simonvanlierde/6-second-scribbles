<script lang="ts">
import { untrack } from "svelte";
import DrawingPhase from "@/components/DrawingPhase.svelte";
import GuessingPhase from "@/components/GuessingPhase.svelte";
import { t } from "@/i18n";
import { useGameStore } from "@/stores/game.svelte";

const store = useGameStore();
const gamePhase = $derived(store.gamePhase);
let drawingPhase = $state<ReturnType<typeof DrawingPhase> | null>(null);

// Submit before switching the branch, while its drawing canvas is still available.
$effect.pre(() => {
  if (gamePhase === "guessing") untrack(() => drawingPhase?.endDrawingPhase());
});
</script>

  {#if gamePhase === 'drawing'}<DrawingPhase bind:this={drawingPhase} />
  {:else if gamePhase === 'guessing'}<GuessingPhase />
  {:else}<main class="flex min-h-screen items-center justify-center">
    <div class="container">
      <h1>{t('game.waitingForRound')}</h1>
    </div>
  </main>
{/if}
