// Small utility to map client coordinates to canvas CSS coordinates.
export function clientToCanvasCoords(canvas: HTMLCanvasElement | null, clientX: number, clientY: number) {
  if (!canvas) return { x: 0, y: 0 }
  const rect = canvas.getBoundingClientRect()
  return {
    x: clientX - rect.left,
    y: clientY - rect.top,
  }
}
