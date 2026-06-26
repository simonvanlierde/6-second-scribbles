/**
 * Export a single drawing as a downloadable PNG.
 *
 * Drawings are stored as transparent PNG data URLs (the canvas is never
 * background-filled). For a standalone file we composite the strokes over a
 * cream background so the export matches the in-game paper look.
 */

// Hardcoded, NOT var(--color-paper): the paper token resolves to a dark value in
// dark mode, but an exported drawing should always be cream.
const CREAM = "#FDFBF7";

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Failed to load drawing image"));
    img.src = src;
  });
}

export function useDrawingExport() {
  async function exportDrawing(dataUrl: string, filename: string): Promise<void> {
    const img = await loadImage(dataUrl);

    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.fillStyle = CREAM;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);

    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = filename;
    link.click();
  }

  return { exportDrawing };
}
