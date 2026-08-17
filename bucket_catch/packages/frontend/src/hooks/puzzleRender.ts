import type { FallingPuzzleItem } from "../types";
import {
  BASKET_HALF_WIDTH,
  BASKET_HEIGHT,
  PIECE_HALF_H,
  PIECE_HALF_W,
} from "./puzzleGeometry";

/**
 * Canvas drawing for the puzzle game.
 *
 * Nothing here reads or writes game state — each function takes what it needs
 * and paints. Keeping the rendering separate from the tick means the loop in
 * `usePuzzleGameLoop` reads as scheduling and collision, not as drawing calls.
 */

export function drawBasket(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
): void {
  const h = BASKET_HEIGHT;
  ctx.save();
  ctx.strokeStyle = "#f472b6";
  ctx.lineWidth = 4;
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(x - BASKET_HALF_WIDTH, y - h / 2);
  ctx.lineTo(x - BASKET_HALF_WIDTH, y + h / 2);
  ctx.lineTo(x + BASKET_HALF_WIDTH, y + h / 2);
  ctx.lineTo(x + BASKET_HALF_WIDTH, y - h / 2);
  ctx.stroke();
  ctx.strokeStyle = "#e879f9";
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.moveTo(x - BASKET_HALF_WIDTH - 6, y - h / 2);
  ctx.lineTo(x + BASKET_HALF_WIDTH + 6, y - h / 2);
  ctx.stroke();
  ctx.restore();
}

export function drawPiece(
  ctx: CanvasRenderingContext2D,
  item: FallingPuzzleItem,
  img: HTMLImageElement | undefined,
  caught: boolean,
): void {
  const w = PIECE_HALF_W * 2;
  const h = PIECE_HALF_H * 2;
  const x = item.x - PIECE_HALF_W;
  const y = item.y - PIECE_HALF_H;

  ctx.save();
  ctx.globalAlpha = caught ? 0.35 : 1;

  if (img?.complete && img.naturalWidth > 0) {
    ctx.drawImage(img, x, y, w, h);
  } else {
    ctx.fillStyle = "rgba(129, 140, 248, 0.5)";
    ctx.fillRect(x, y, w, h);
  }

  ctx.strokeStyle = caught ? "#34d399" : "#f472b6";
  ctx.lineWidth = caught ? 3 : 2;
  ctx.strokeRect(x, y, w, h);
  ctx.restore();
}

export function drawHUD(
  ctx: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  caught: number,
  total: number,
  piecesDone: number,
): void {
  ctx.save();
  ctx.fillStyle = "rgba(0,0,0,0.45)";
  ctx.roundRect(canvas.width - 160, 12, 148, 36, 8);
  ctx.fill();
  ctx.fillStyle = "#a5b4fc";
  ctx.font = "bold 14px monospace";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.fillText(`✅ ${caught} / ${total}`, canvas.width - 20, 30);
  ctx.restore();

  const barW = 200;
  const barX = (canvas.width - barW) / 2;
  ctx.save();
  ctx.fillStyle = "rgba(0,0,0,0.4)";
  ctx.roundRect(barX, 12, barW, 8, 4);
  ctx.fill();
  ctx.fillStyle = "#818cf8";
  ctx.roundRect(barX, 12, barW * (piecesDone / total), 8, 4);
  ctx.fill();
  ctx.restore();
}

/** Paints the backdrop gradient the pieces fall against. */
export function drawBackdrop(
  ctx: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
): void {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
  grad.addColorStop(0, "#0f0c29");
  grad.addColorStop(1, "#302b63");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}
