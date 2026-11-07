<script lang="ts">
import HdDialog from "@/components/ui/HdDialog.svelte";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { useRoomLeave } from "@/composables/useRoomLeave.svelte";

const roomLeave = useRoomLeave();
const { leaveRoom } = useLeaveRoom();
let open = $state(false);

/** Leave now, or ask first when leaving costs the player their round or the room its host. */
function request() {
  if (roomLeave.shouldConfirm) open = true;
  else leaveRoom();
}

export { request };
</script>

<HdDialog
  bind:open
  title={roomLeave.dialog.title}
  message={roomLeave.dialog.message}
  confirmLabel={roomLeave.dialog.confirmLabel}
  cancelLabel={roomLeave.dialog.cancelLabel}
  variant="danger"
  onconfirm={leaveRoom}
></HdDialog>
