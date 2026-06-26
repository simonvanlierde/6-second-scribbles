import { defineStore } from "pinia";
import { ref } from "vue";

import type { DrawStroke } from "@/shared/types";

export const useDrawingStore = defineStore(
  "drawing",
  () => {
    const currentStrokes = ref<DrawStroke[]>([]);
    const localPadVisible = ref<boolean>(true);
    const roomPadVisible = ref<boolean>(true);

    function addStroke(stroke: DrawStroke) {
      currentStrokes.value.push(stroke);
    }

    function clearStrokes() {
      currentStrokes.value = [];
    }

    function setRoomPadVisible(visible: boolean) {
      roomPadVisible.value = visible;
    }

    function setLocalPadVisible(visible: boolean) {
      localPadVisible.value = visible;
    }

    return {
      currentStrokes,
      localPadVisible,
      roomPadVisible,
      addStroke,
      clearStrokes,
      setRoomPadVisible,
      setLocalPadVisible,
    };
  },
  {
    persist: {
      pick: ["localPadVisible"],
    },
  },
);
