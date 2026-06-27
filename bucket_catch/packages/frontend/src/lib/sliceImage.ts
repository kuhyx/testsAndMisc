import type { PuzzlePiece } from "../types";

/** Slice an image file into a gridSize×gridSize grid of data-URL pieces. */
export function sliceImage(file: File, gridSize: number): Promise<PuzzlePiece[]> {
  return new Promise<PuzzlePiece[]>((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);

    img.onload = () => {
      const pieceWidth = Math.floor(img.width / gridSize);
      const pieceHeight = Math.floor(img.height / gridSize);
      const pieces: PuzzlePiece[] = [];

      for (let row = 0; row < gridSize; row++) {
        for (let col = 0; col < gridSize; col++) {
          const offscreen = document.createElement("canvas");
          offscreen.width = pieceWidth;
          offscreen.height = pieceHeight;
          const ctx = offscreen.getContext("2d");
          /* istanbul ignore next */
          if (!ctx) {
            URL.revokeObjectURL(url);
            reject(new Error("Canvas 2D context not available"));
            return;
          }
          ctx.drawImage(
            img,
            col * pieceWidth,
            row * pieceHeight,
            pieceWidth,
            pieceHeight,
            0,
            0,
            pieceWidth,
            pieceHeight,
          );
          pieces.push({
            row,
            col,
            gridSize,
            imageUrl: offscreen.toDataURL(),
            pieceWidth,
            pieceHeight,
          });
        }
      }

      URL.revokeObjectURL(url);
      resolve(pieces);
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Failed to load image for slicing"));
    };

    img.src = url;
  });
}
