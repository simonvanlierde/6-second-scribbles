<script setup lang="ts">
import { ref } from "vue";

import HdDialog from "@/components/ui/HdDialog.vue";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { useRoomLeave } from "@/composables/useRoomLeave";

const { shouldConfirm, dialog } = useRoomLeave();
const { leaveRoom } = useLeaveRoom();
const open = ref(false);

/** Leave now, or ask first when leaving costs the player their round or the room its host. */
function request() {
  if (shouldConfirm.value) open.value = true;
  else leaveRoom();
}

defineExpose({ request });
</script>

<template>
  <HdDialog
    v-model:open="open"
    :title="dialog.title"
    :message="dialog.message"
    :confirm-label="dialog.confirmLabel"
    :cancel-label="dialog.cancelLabel"
    variant="danger"
    @confirm="leaveRoom"
  />
</template>
