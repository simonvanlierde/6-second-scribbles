import { ref } from 'vue'

import type { DrawStroke } from '@/shared/types'
import logger from '@/utils/logger'

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
  const onStrokeProgress = ref<
    | ((partial: { color: string; width: number; points: Array<{ x: number; y: number }> }) => void)
    | null
  >(null)

  // Prevent-default handlers for touch events (stable references so we can remove them)
  const onTouchStartPrevent = (e: Event) => e.preventDefault()
  const onTouchMovePrevent = (e: Event) => e.preventDefault()

  function initCanvas(canvas: HTMLCanvasElement) {
    // Clean up old listeners if re-initializing
    removeEventListeners()

    canvasRef.value = canvas
    let context = canvas.getContext('2d')

    // In some test environments (jsdom) canvas.getContext may return null.
    // Provide a lightweight no-op mock context so the drawing composable can
    // be exercised in unit tests without failing. The mock implements the
    // subset of CanvasRenderingContext2D used by the app.
    if (!context) {
      logger.debug('[useDrawingCanvas] 2D context unavailable; using mock context for tests')
      const mockContext: unknown = {
        // drawing state
        strokeStyle: '#000',
        lineWidth: 1,
        lineCap: 'round',
        lineJoin: 'round',
        // no-op drawing methods
        beginPath: () => {},
        moveTo: (_x: number, _y: number) => {},
        lineTo: (_x: number, _y: number) => {},
        stroke: () => {},
        clearRect: (_x: number, _y: number, _w: number, _h: number) => {},
        drawImage: (
          _img: CanvasImageSource,
          _sx?: number,
          _sy?: number,
          _sw?: number,
          _sh?: number
        ) => {},
        setTransform: (
          _a: number,
          _b: number,
          _c: number,
          _d: number,
          _e: number,
          _f: number
        ) => {},
        fillRect: (_x: number, _y: number, _w: number, _h: number) => {},
        measureText: (_text: string) => ({ width: 0 }),
      }
      context = mockContext as CanvasRenderingContext2D
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
    // Remove canvas listeners if present
    if (canvasRef.value) {
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

      // Prevent scrolling handlers
      canvasRef.value.removeEventListener('touchstart', onTouchStartPrevent)
      canvasRef.value.removeEventListener('touchmove', onTouchMovePrevent)
    }

    // Window resize listener
    window.removeEventListener('resize', resize)
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
    canvasRef.value.addEventListener('touchstart', onTouchStartPrevent)
    canvasRef.value.addEventListener('touchmove', onTouchMovePrevent)

    // Respond to viewport resize to recompute scaling/internal buffer
    window.addEventListener('resize', resize)
  }

  function getCoordinates(event: MouseEvent | TouchEvent): { x: number; y: number } {
    if (!canvasRef.value) return { x: 0, y: 0 }
    const rect = canvasRef.value.getBoundingClientRect()

    const clientX = event instanceof MouseEvent ? event.clientX : event.touches[0]?.clientX || 0
    const clientY = event instanceof MouseEvent ? event.clientY : event.touches[0]?.clientY || 0

    // Determine logical size (the canonical drawing area) from data attrs if provided
    const logicalWidth = Number(canvasRef.value.dataset.logicalWidth) || canvasRef.value.clientWidth
    const logicalHeight =
      Number(canvasRef.value.dataset.logicalHeight) || canvasRef.value.clientHeight

    // The element may be visually scaled via CSS transform; compute scale factor
    const scaleX = rect.width / logicalWidth || 1
    const scaleY = rect.height / logicalHeight || 1
    const scale = Math.max(scaleX, scaleY) || 1

    // Map client coordinates into logical canvas coordinates
    const x = (clientX - rect.left) / scale - (canvasRef.value.clientLeft || 0)
    const y = (clientY - rect.top) / scale - (canvasRef.value.clientTop || 0)
    return { x, y }
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

  function setStrokeProgressCallback(
    cb:
      | ((partial: {
          color: string
          width: number
          points: Array<{ x: number; y: number }>
        }) => void)
      | null
  ) {
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

    // Determine canonical logical size from data attributes (defaults to current client size)
    const logicalWidth = Number(canvasRef.value.dataset.logicalWidth) || 800
    const logicalHeight = Number(canvasRef.value.dataset.logicalHeight) || 500
    const dpr = window.devicePixelRatio || 1

    // Compute scale to fit into parent width but never exceed 1 (no upscaling)
    const parent = canvasRef.value.parentElement || document.body
    const parentWidth = parent.clientWidth
    const scale = Math.min(1, parentWidth / logicalWidth)

    // Set CSS size to the logical size; visual scaling is handled by transform
    canvasRef.value.style.width = `${logicalWidth}px`
    canvasRef.value.style.height = `${logicalHeight}px`
    canvasRef.value.style.transformOrigin = 'top left'
    canvasRef.value.style.transform = `scale(${scale})`

    // Set the internal pixel buffer according to logical size and DPR
    canvasRef.value.width = Math.round(logicalWidth * dpr)
    canvasRef.value.height = Math.round(logicalHeight * dpr)

    // Reset and scale drawing context so drawing coordinates map to logical CSS pixels
    ctx.value.setTransform(dpr, 0, 0, dpr, 0, 0)

    // Restore previous drawing from data URL into logical coordinate space
    if (dataUrl) {
      const image = new Image()
      image.onload = () => {
        try {
          ctx.value!.clearRect(0, 0, logicalWidth, logicalHeight)
          ctx.value!.drawImage(image, 0, 0, logicalWidth, logicalHeight)
        } catch (err) {
          logger.debug('restore drawing failed', err)
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

  function cleanup() {
    // Remove event listeners and clear canvas state
    removeEventListeners()
    try {
      clear()
    } catch {
      // ignore errors during cleanup
    }
    // Null out refs so re-init is possible
    canvasRef.value = null
    ctx.value = null
    onStrokeProgress.value = null
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
    cleanup,
    setStrokeProgressCallback,
  }
}

// The composable may internally use clientToCanvasCoords when needed.
