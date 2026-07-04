<script setup lang="ts">
import { computed } from "vue";

interface Props {
  seconds: number;
  urgentAt?: number;
}

const props = withDefaults(defineProps<Props>(), { urgentAt: 10 });

const isUrgent = computed(() => props.seconds <= props.urgentAt);
</script>

<template>
  <div class="hd-timer" :class="isUrgent ? 'hd-timer--urgent' : 'hd-timer--calm'" aria-hidden="true">
    <!-- aria-hidden: a per-second live region would make screen readers announce
         every tick. The countdown is a visual urgency cue only. -->
    {{ props.seconds }}
  </div>
</template>

<style scoped>
.hd-timer {
  display: inline-block;
  padding: 6px 18px;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 2.4rem;
  line-height: 1.05;
  border: 2.5px solid var(--color-ink);
  border-radius: 14px 22px 16px 12px;
  box-shadow: 4px 4px 0 var(--color-ink);
  min-width: 4rem;
  text-align: center;
  font-variant-numeric: tabular-nums;
  transform: rotate(-1deg);
  transition:
    background-color var(--motion-fast) var(--ease-out),
    color var(--motion-fast) var(--ease-out);
}
.hd-timer--calm {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
.hd-timer--urgent {
  background: var(--color-marker-red);
  color: white;
  animation: heartbeat 1s var(--ease-spring) infinite;
}
@keyframes heartbeat {
  0%,
  100% {
    transform: rotate(-1deg) scale(1);
  }
  50% {
    transform: rotate(-1deg) scale(1.04);
  }
}
@media (prefers-reduced-motion: reduce) {
  .hd-timer--urgent {
    animation: none;
  }
}
</style>
