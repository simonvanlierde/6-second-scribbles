<template>
  <div class="toast-root" aria-live="polite">
    <div v-for="n in notifications" :key="n.id" class="toast-item">
      <span>{{ n.text }}</span>
      <button
        v-if="n.undo"
        class="toast-undo"
        @click="
          () => {
            n.undo && n.undo()
            onDismiss(n.id)
          }
        "
      >
        Undo
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useNotifications, dismissNotification } from '@/composables/notifications'
const { notifications } = useNotifications()

function onDismiss(id: number) {
  dismissNotification(id)
}
</script>

<!-- styles moved to src/assets/main.css -->
