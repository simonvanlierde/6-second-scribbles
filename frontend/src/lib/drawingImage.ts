// The backend drops any WebSocket frame over 64 KiB (ws_max_message_bytes), and
// the data URL travels inside a JSON message, so keep a margin under that.
export const MAX_DRAWING_CHARS = 56 * 1024;

// Longest side, in pixels, of each attempt. The guessing view shows a drawing at
// most about 1000 CSS px wide, so 1024 px is enough; a HiDPI canvas is often
// twice that. Smaller sizes are only used when a dense drawing is over budget.
const SIDES = [1024, 800, 640, 512, 384];
const WEBP_QUALITIES = [0.8, 0.5];

/**
 * Encode a finished drawing as a data URL that fits in one WebSocket message.
 *
 * The strokes are painted over `background` (the colour the drawer saw):
 * WebP compresses the alpha channel losslessly, so a transparent image of a
 * busy drawing is about 1.5x the size of an opaque one. Browsers without a
 * WebP encoder get PNG. If nothing fits, the smallest attempt is returned.
 */
export function encodeDrawing(source: HTMLCanvasElement, background: string): string {
  const longest = Math.max(source.width, source.height, 1);
  let smallest = "";
  for (const side of SIDES) {
    const scale = Math.min(1, side / longest);
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(source.width * scale));
    canvas.height = Math.max(1, Math.round(source.height * scale));
    const ctx = canvas.getContext("2d");
    if (!ctx) return source.toDataURL("image/png");
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(source, 0, 0, canvas.width, canvas.height);

    for (const quality of WEBP_QUALITIES) {
      let dataUrl = canvas.toDataURL("image/webp", quality);
      // Browsers that cannot encode WebP return a PNG instead.
      if (!dataUrl.startsWith("data:image/webp")) dataUrl = canvas.toDataURL("image/png");
      if (dataUrl.length <= MAX_DRAWING_CHARS) return dataUrl;
      if (!smallest || dataUrl.length < smallest.length) smallest = dataUrl;
      if (!dataUrl.startsWith("data:image/webp")) break;
    }
    if (scale === 1) break;
  }
  return smallest;
}
