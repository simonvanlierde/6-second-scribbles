import { ref } from 'vue'

import type { DrawStroke } from '@/shared/types'

export function useDrawingCanvas() {
  // Declare and initialize all properties
  const canvasRef = ref<HTMLCanvasElement | null>(null)
  const ctx = ref<CanvasRenderingContext2D | null>(null)
  const isDrawing = ref(false)
  const currentStroke = ref<{ x: number; y: number }[]>([])
  const strokes = ref<DrawStroke[]>([])
  const currentColor = ref('#000000')
  const currentWidth = ref(5)
  // Optional callback for incremental stroke progress (points appended while drawing)
  const onStrokeProgress = ref<((partial: { color: string; width: number; points: Array<{ x: number; y: number }> }) => void) | null>(null)

  function initCanvas(canvas: HTMLCanvasElement) {
    // Clean up old listeners if re-initializing
    removeEventListeners()

    canvasRef.value = canvas
    const context = canvas.getContext('2d')
    if (!context) {
      throw new Error('Could not get 2D context from canvas')
    }
    ctx.value = context

    // Set canvas size
    resize()

    // Set up drawing style
    context.lineCap = 'round'
    context.lineJoin = 'round'

    // Set up event listeners
    setupEventListeners()
  }

  function removeEventListeners() {
    if (!canvasRef.value) return

    // Mouse events
    canvasRef.value.removeEventListener('mousedown', startDrawing)
    canvasRef.value.removeEventListener('mousemove', draw)
    canvasRef.value.removeEventListener('mouseup', stopDrawing)
    canvasRef.value.removeEventListener('mouseleave', stopDrawing)

    // Touch events
    canvasRef.value.removeEventListener('touchstart', handleTouchStart)
    canvasRef.value.removeEventListener('touchmove', handleTouchMove)
    canvasRef.value.removeEventListener('touchend', stopDrawing)
    canvasRef.value.removeEventListener('touchcancel', stopDrawing)
  }

  function setupEventListeners() {
    if (!canvasRef.value) return

    // Mouse events
    canvasRef.value.addEventListener('mousedown', startDrawing)
    canvasRef.value.addEventListener('mousemove', draw)
    canvasRef.value.addEventListener('mouseup', stopDrawing)
    canvasRef.value.addEventListener('mouseleave', stopDrawing)

    // Touch events for mobile
    canvasRef.value.addEventListener('touchstart', handleTouchStart)
    canvasRef.value.addEventListener('touchmove', handleTouchMove)
    canvasRef.value.addEventListener('touchend', stopDrawing)
    canvasRef.value.addEventListener('touchcancel', stopDrawing)

    // Prevent scrolling on touch
    canvasRef.value.addEventListener('touchstart', (e) => e.preventDefault())
    canvasRef.value.addEventListener('touchmove', (e) => e.preventDefault())
  }

  function getCoordinates(event: MouseEvent | TouchEvent): { x: number; y: number } {
    if (!canvasRef.value) return { x: 0, y: 0 }

    const rect = canvasRef.value.getBoundingClientRect()

    if (event instanceof MouseEvent) {
      return {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      }
    } else {
      const touch = event.touches[0]
      if (!touch) return { x: 0, y: 0 }
      return {
        x: touch.clientX - rect.left,
        y: touch.clientY - rect.top,
      }
    }
  }


  function startDrawing(event: MouseEvent | TouchEvent) {
    if (!ctx.value) return
    isDrawing.value = true
    const coords = getCoordinates(event)
    currentStroke.value = [coords]

    ctx.value.beginPath()
    ctx.value.moveTo(coords.x, coords.y)
  }

  function draw(event: MouseEvent | TouchEvent) {
    if (!isDrawing.value || !ctx.value) return

    const coords = getCoordinates(event)
    currentStroke.value.push(coords)

    ctx.value.strokeStyle = currentColor.value
    ctx.value.lineWidth = currentWidth.value
    ctx.value.lineTo(coords.x, coords.y)
    ctx.value.stroke()

    // Emit incremental progress to the optional callback
    if (onStrokeProgress.value) {
      onStrokeProgress.value({
        color: currentColor.value,
        width: currentWidth.value,
        points: [...currentStroke.value],
      })
    }
  }

  function stopDrawing() {
    if (!isDrawing.value) return

    isDrawing.value = false

    if (currentStroke.value.length > 0) {
      const stroke: DrawStroke = {
        points: currentStroke.value,
        color: currentColor.value,
        width: currentWidth.value,
      }

      strokes.value.push(stroke)
      currentStroke.value = []
    }
  }

  function setStrokeProgressCallback(cb: ((partial: { color: string; width: number; points: Array<{ x: number; y: number }> }) => void) | null) {
    onStrokeProgress.value = cb
  }

  function handleTouchStart(event: TouchEvent) {
    startDrawing(event)
  }

  function handleTouchMove(event: TouchEvent) {
    draw(event)
  }

  function setColor(color: string) {
    currentColor.value = color
  }

  function setWidth(width: number) {
    currentWidth.value = width
  }

  function clear() {
    if (!ctx.value || !canvasRef.value) return
    ctx.value.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
    strokes.value = []
  }

  function resize() {
    if (!canvasRef.value || !ctx.value) return
    // Preserve drawing via dataURL (safer across DPI changes)
    const dataUrl = canvasRef.value.toDataURL()

    const parent = canvasRef.value.parentElement
    if (!parent) return

    const cssWidth = parent.clientWidth
    const cssHeight = parent.clientHeight
    const dpr = window.devicePixelRatio || 1

    // Set the internal pixel size for high-DPI displays
    canvasRef.value.width = Math.round(cssWidth * dpr)
    canvasRef.value.height = Math.round(cssHeight * dpr)

    // Keep CSS size unchanged
    canvasRef.value.style.width = `${cssWidth}px`
    canvasRef.value.style.height = `${cssHeight}px`

    // Reset and scale drawing context so drawing coordinates map to CSS pixels
    ctx.value.setTransform(dpr, 0, 0, dpr, 0, 0)

    // Restore previous drawing from data URL
    if (dataUrl) {
      const image = new Image()
      image.onload = () => {
        try {
          // drawImage uses CSS-space coordinates because we've setTransform(dpr,...)
          ctx.value!.clearRect(0, 0, cssWidth, cssHeight)
          ctx.value!.drawImage(image, 0, 0, cssWidth, cssHeight)
        } catch (err) {
          // sometimes test DOMs throw on drawImage; ignore but log at debug level
          console.debug('restore drawing failed', err)
        }
      }
      image.src = dataUrl
    }
  }

  function drawStroke(stroke: DrawStroke) {
    if (!ctx.value || stroke.points.length === 0) return

    const firstPoint = stroke.points[0]
    if (!firstPoint) return

    ctx.value.strokeStyle = stroke.color
    ctx.value.lineWidth = stroke.width
    ctx.value.beginPath()
    ctx.value.moveTo(firstPoint.x, firstPoint.y)

    for (let i = 1; i < stroke.points.length; i++) {
      const point = stroke.points[i]
      if (point) {
        ctx.value.lineTo(point.x, point.y)
      }
    }

    ctx.value.stroke()
  }

  function toDataURL(): string {
    return canvasRef.value?.toDataURL() || ''
  }

  function loadDrawing(dataUrl: string) {
    const canvas = canvasRef.value
    const context = ctx.value
    if (canvas && context) {
      const image = new Image()
      image.onload = () => {
        context.clearRect(0, 0, canvas.width, canvas.height)
        context.drawImage(image, 0, 0)
      }
      image.src = dataUrl
    }
  }

  return {
    canvasRef,
    isDrawing,
    currentColor,
    currentWidth,
    strokes,
    initCanvas,
    setColor,
    setWidth,
    clear,
    resize,
    drawStroke,
    toDataURL,
    loadDrawing,
    setStrokeProgressCallback,
  }
}

// The composable may internally use clientToCanvasCoords when needed.
