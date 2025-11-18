// Small utility to map client coordinates to canvas CSS coordinates.
export function clientToCanvasCoords(
  canvas: HTMLCanvasElement | null,
  clientX: number,
  clientY: number
) {
  if (!canvas) return { x: 0, y: 0 }
  const rect = canvas.getBoundingClientRect()
  const left = canvas.clientLeft || 0
  const top = canvas.clientTop || 0

  // Map client coords to CSS pixel coordinates inside the canvas drawing area
  return {
    x: clientX - rect.left - left,
    y: clientY - rect.top - top,
  }
}
