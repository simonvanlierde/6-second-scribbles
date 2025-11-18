<template>
  <div class="shared-drawpad">
    <div class="drawpad-viewport">
      <div class="canvas-tools">
        <div class="tool-group">
          <label>Color:</label>
          <input
            class="color-picker"
            type="color"
            v-model="colorPicker"
            :disabled="activeTool === 'eraser'"
          />
        </div>
        <div class="tool-group">
          <label>Size:</label>
          <input type="range" :min="minBrushSize" :max="maxBrushSize" v-model.number="width" />
          <small style="margin-left: 0.5rem">{{ width }}</small>
        </div>
        <div class="tool-group">
          <!-- Pen / Eraser tools visible to all -->
          <button
            class="btn btn-icon"
            :class="{ active: activeTool === 'pen' }"
            @click="selectTool('pen')"
            title="Pen"
          >
            ✏️
          </button>
          <button
            class="btn btn-icon"
            :class="{ active: activeTool === 'eraser' }"
            @click="selectTool('eraser')"
            title="Eraser"
          >
            🧽
          </button>
        </div>
        <!-- drawing toolbar only (visibility and host actions managed by WaitingRoomView) -->
      </div>
      <div class="canvas-area">
        <canvas ref="canvasEl" class="mini-canvas"></canvas>
      </div>
    </div>
    <p class="drawpad-hint">Draw together with other players while waiting!</p>
    <!-- visibility and host actions live in WaitingRoomView -->
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { useDrawingCanvas } from '@/composables/useDrawingCanvas'
import { useGameConnection } from '@/composables/useGameConnection'
import { useGameStore } from '@/stores/game'
// notifications and confirm dialog are handled by the parent view

const props = defineProps({
  mode: { type: String as () => 'compact' | 'normal' | 'large' | undefined, default: undefined },
  logicalWidth: { type: Number, default: 800 },
  logicalHeight: { type: Number, default: 500 },
  // Brush size overrides so callers can adjust per-embed
  minBrushSize: { type: Number, default: 1 },
  maxBrushSize: { type: Number, default: 40 },
  defaultBrushSize: { type: Number, default: 5 },
})

// Map mode presets to sizes
const presetSizes: Record<string, { w: number; h: number }> = {
  compact: { w: 680, h: 420 },
  normal: { w: 800, h: 500 },
  large: { w: 1000, h: 600 },
}

const modeKey = props.mode && presetSizes[props.mode] ? props.mode : undefined
const resolvedWidth = (modeKey && presetSizes[modeKey]?.w) || props.logicalWidth
const resolvedHeight = (modeKey && presetSizes[modeKey]?.h) || props.logicalHeight

const canvas = useDrawingCanvas()
const canvasEl = ref<HTMLCanvasElement | null>(null)
const store = useGameStore()
const { send } = useGameConnection()

// Keep reactive references to prop values for template access
const minBrushSize = props.minBrushSize
const maxBrushSize = props.maxBrushSize

// visibility/host actions are handled by the parent view now

const color = ref('#444444')
const colorPicker = ref('#444444')
// initialize width using prop default
const width = ref(props.defaultBrushSize)
const activeTool = ref<'pen' | 'eraser'>('pen')
const canvasBgColor = ref('#ffffff')
let savedColor = ''
let savedWidth = 0

function selectTool(tool: 'pen' | 'eraser') {
  if (tool === activeTool.value) return
  if (tool === 'eraser') {
    // enable eraser: save current settings and switch to canvas background
    savedColor = colorPicker.value
    savedWidth = width.value
    color.value = canvasBgColor.value || '#ffffff'
    // ensure eraser has a reasonably large width but clamp to configured max
    width.value = Math.min(props.maxBrushSize, Math.max(12, savedWidth || 12))
    activeTool.value = 'eraser'
  } else {
    // restore pen
    color.value = savedColor || '#444444'
    width.value = savedWidth || props.defaultBrushSize
    activeTool.value = 'pen'
  }
}

// clearForEveryone, toggleRoomVisibility, toggleLocalShow moved to WaitingRoomView

// room-level clear/visibility actions moved to WaitingRoomView

onMounted(() => {
  if (canvasEl.value) {
    // expose logical size for the composable to read (mode overrides numeric props)
    canvasEl.value.dataset.logicalWidth = String(resolvedWidth)
    canvasEl.value.dataset.logicalHeight = String(resolvedHeight)
    canvas.initCanvas(canvasEl.value)
    // determine canvas background color to use for eraser
    try {
      const computed = getComputedStyle(canvasEl.value)
      const bg = computed.backgroundColor
      if (bg) canvasBgColor.value = bg
    } catch {
      // ignore
    }
    // initialize drawing color from the picker when mounted
    if (activeTool.value === 'pen') {
      color.value = colorPicker.value
    }
    canvas.setColor(color.value)
    canvas.setWidth(width.value)

    // draw existing strokes
    if (store.currentStrokes.length > 0) {
      store.currentStrokes.forEach((s) => canvas.drawStroke(s))
    }

    // send partials via rAF; using the composable callback to receive progress
    type StrokePartial = { color: string; width: number; points: Array<{ x: number; y: number }> }
    let latestPartial: StrokePartial | null = null
    let rafId: number | null = null
    function scheduleSend() {
      if (rafId !== null) return
      rafId = requestAnimationFrame(() => {
        rafId = null
        if (latestPartial && store.localPlayerId) {
          send({
            type: 'draw_stroke_partial',
            playerId: store.localPlayerId,
            stroke: latestPartial,
          })
        }
      })
    }

    canvas.setStrokeProgressCallback((partial) => {
      latestPartial = partial
      scheduleSend()
    })

    // draw incoming strokes from store
    watch(
      () => store.currentStrokes,
      (strokes) => {
        // If the strokes array was replaced (e.g. on join or restore), redraw all
        if (strokes.length === 0) {
          canvas.clear()
        } else {
          // Clear and redraw all strokes to ensure full sync
          canvas.clear()
          strokes.forEach((s) => canvas.drawStroke(s))
        }
      },
      { deep: true }
    )

    // Watch local composable strokes so completed local strokes are added to
    // the shared store and sent to the server as final strokes. This prevents
    // local-only strokes from being lost when the store later redraws from
    // persisted strokes.
    let prevStrokeCount = canvas.strokes.value.length
    watch(
      () => canvas.strokes.value.length,
      (len, old) => {
        // If new strokes were appended locally, forward them
        if (len > (old ?? prevStrokeCount)) {
          const newStrokes = canvas.strokes.value.slice(old ?? prevStrokeCount)
          newStrokes.forEach((s) => {
            // add to the shared store so redraws include the local stroke
            store.addStroke(s)
            // send final stroke to server for persistence and relay
            if (store.localPlayerId) {
              send({ type: 'draw_stroke', playerId: store.localPlayerId, stroke: s })
            }
          })
        }
        prevStrokeCount = len
      }
    )

    // sync drawing color/width
    watch(color, (v) => canvas.setColor(v))
    watch(width, (v) => canvas.setWidth(v))
    // when the visible color picker changes and we are in pen mode, update drawing color
    watch(colorPicker, (v) => {
      if (activeTool.value === 'pen') {
        color.value = v
      }
    })

    onUnmounted(() => {
      canvas.canvasRef.value = null
      if (rafId) cancelAnimationFrame(rafId)
    })
  }
})

// Expose useful API for parent components (GameView) to call
defineExpose({
  loadDrawing: canvas.loadDrawing,
  toDataURL: canvas.toDataURL,
  clear: canvas.clear,
  setColor: canvas.setColor,
  setWidth: canvas.setWidth,
  canvasRef: canvas.canvasRef,
})
</script>

<style scoped>
.canvas-tools {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background-color: white;
  border-radius: 4px;
  align-items: center;
}
.canvas-tools {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background-color: white;
  border-radius: 4px;
  align-items: center;
  /* make controls align to canvas width so they don't cause horizontal overflow */
  max-width: var(--drawpad-width, 800px);
  width: 100%;
  box-sizing: border-box;
  justify-content: space-between;
}
.drawpad-viewport {
  overflow: auto;
  width: 100%;
  display: flex;
  justify-content: center;
}
.drawpad-viewport {
  overflow: auto;
  width: 100%;
  display: flex;
  justify-content: center;
  /* stack controls above canvas on narrow viewports */
  flex-direction: column;
  align-items: center;
}
.canvas-area {
  /* ensures canvas sits at defined size and can be scrolled on small screens */
  display: block;
}
.tool-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.tool-group label {
  font-weight: 500;
  font-size: 0.875rem;
  color: #495057;
}
.mini-canvas {
  /* fixed visual size so all participants share same drawing area
     wrapped in a scrollable container for small viewports */
  --drawpad-width: 800px;
  --drawpad-height: 500px;
  width: var(--drawpad-width);
  height: var(--drawpad-height);
  border: 2px solid #dee2e6;
  border-radius: 4px;
  cursor: crosshair;
  background: white;
  display: block;
  margin: 0 auto;
}
.drawpad-hint {
  text-align: center;
  color: #6c757d;
  font-size: 0.875rem;
  margin-top: 0.5rem;
  font-style: italic;
}

.btn-icon {
  background: transparent;
  border: none;
  padding: 0.25rem 0.5rem;
  font-size: 1rem;
  cursor: pointer;
}
.btn-icon.active {
  background: rgba(0, 123, 255, 0.08);
  border-radius: 4px;
}
/* make the color swatch larger and clearly interactive */
.color-picker {
  cursor: pointer;
  -webkit-appearance: none;
  appearance: none;
  width: 2.25rem;
  height: 2.25rem;
  padding: 0.15rem;
  border-radius: 6px;
  border: 2px solid rgba(0, 0, 0, 0.08);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) inset;
  transition:
    box-shadow 120ms ease,
    transform 120ms ease,
    border-color 120ms ease;
}
.color-picker:hover {
  transform: translateY(-1px);
  border-color: rgba(0, 0, 0, 0.12);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08) inset;
}
.color-picker:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.12);
  border-color: rgba(0, 123, 255, 0.5);
}

/* Host controls visual separator and emphasis */
.host-controls {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  padding-top: 0.5rem;
  margin-top: 0.5rem;
  align-items: center;
}
.btn-danger {
  color: #b02a37;
  border: 1px solid rgba(176, 42, 55, 0.12);
  background: transparent;
  transition:
    background-color 120ms ease,
    color 120ms ease;
}
.btn-danger:hover {
  background: rgba(176, 42, 55, 0.06);
}
.host-badge {
  background: rgba(0, 0, 0, 0.02);
  padding: 0.125rem 0.4rem;
  border-radius: 4px;
}
</style>
