<template>
  <div class="game-drawpad">
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
        <div class="tool-group">
          <button class="btn btn-small" @click="clearCanvas">Clear</button>
        </div>
      </div>
      <div class="canvas-area">
        <canvas ref="canvasEl" class="mini-canvas"></canvas>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { useDrawingCanvas } from '@/composables/useDrawingCanvas'

const props = defineProps({
  mode: { type: String as () => 'compact' | 'normal' | 'large' | undefined, default: undefined },
  logicalWidth: { type: Number, default: 800 },
  logicalHeight: { type: Number, default: 500 },
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

const minBrushSize = props.minBrushSize
const maxBrushSize = props.maxBrushSize

const color = ref('#444444')
const colorPicker = ref('#444444')
const width = ref(props.defaultBrushSize)
const activeTool = ref<'pen' | 'eraser'>('pen')
const canvasBgColor = ref('#ffffff')
let savedColor = ''
let savedWidth = 0

function selectTool(tool: 'pen' | 'eraser') {
  if (tool === activeTool.value) return
  if (tool === 'eraser') {
    savedColor = colorPicker.value
    savedWidth = width.value
    color.value = canvasBgColor.value || '#ffffff'
    width.value = Math.min(props.maxBrushSize, Math.max(12, savedWidth || 12))
    activeTool.value = 'eraser'
  } else {
    color.value = savedColor || '#444444'
    width.value = savedWidth || props.defaultBrushSize
    activeTool.value = 'pen'
  }
}

function clearCanvas() {
  canvas.clear()
}

// Expose methods for parent component to call
function toDataURL(): string {
  return canvas.toDataURL()
}

function loadDrawing(dataURL: string) {
  canvas.loadDrawing(dataURL)
}

function setColor(newColor: string) {
  color.value = newColor
  colorPicker.value = newColor
  canvas.setColor(newColor)
}

function setWidth(newWidth: number) {
  width.value = newWidth
  canvas.setWidth(newWidth)
}

defineExpose({
  toDataURL,
  loadDrawing,
  setColor,
  setWidth,
  clear: clearCanvas,
})

onMounted(() => {
  if (canvasEl.value) {
    canvasEl.value.dataset.logicalWidth = String(resolvedWidth)
    canvasEl.value.dataset.logicalHeight = String(resolvedHeight)
    canvas.initCanvas(canvasEl.value)

    try {
      const computed = getComputedStyle(canvasEl.value)
      const bg = computed.backgroundColor
      if (bg) canvasBgColor.value = bg
    } catch {
      // ignore
    }

    if (activeTool.value === 'pen') {
      color.value = colorPicker.value
    }
    canvas.setColor(color.value)
    canvas.setWidth(width.value)
  }
})

onUnmounted(() => {
  canvas.cleanup()
})
// Watch color and width changes

watch(color, (newColor) => {
  canvas.setColor(newColor)
})

watch(width, (newWidth) => {
  canvas.setWidth(newWidth)
})

watch(colorPicker, (newColor) => {
  if (activeTool.value === 'pen') {
    color.value = newColor
  }
})
</script>

<style scoped>
.game-drawpad {
  width: 100%;
  height: 100%;
}

.drawpad-viewport {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.canvas-tools {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background-color: #f8f9fa;
  border-radius: 4px;
  align-items: center;
  flex-wrap: wrap;
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

.color-picker {
  cursor: pointer;
  width: 40px;
  height: 32px;
  border: 1px solid #ced4da;
  border-radius: 4px;
}

.btn-icon {
  padding: 0.5rem;
  font-size: 1.25rem;
  min-width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon.active {
  background-color: #007bff;
  color: white;
  border-color: #0056b3;
}

.canvas-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f8f9fa;
  border-radius: 4px;
  padding: 1rem;
}

.mini-canvas {
  border: 2px solid #dee2e6;
  border-radius: 4px;
  cursor: crosshair;
  background: white;
  max-width: 100%;
  max-height: 100%;
}
</style>
