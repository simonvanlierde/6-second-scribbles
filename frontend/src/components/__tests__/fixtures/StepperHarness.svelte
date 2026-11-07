<script lang="ts">
import StepperInput from "@/components/StepperInput.svelte";

let modelValue = $state(5);
</script>
<StepperInput bind:modelValue label="Rounds" min={1} max={10} />
<output>{modelValue}</output>
