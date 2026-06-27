import { useCallback, useEffect, useRef, useState } from "react";
import type { FallingFileItem, FileGameResult } from "../types";
import { fileIcon, truncateFilename, formatSize } from "../lib/fileIcon";

const BASKET_HALF_WIDTH = 60;
const BASKET_HEIGHT = 40;
const FILE_HALF_W = 48;
const FILE_HALF_H = 28;
const SPAWN_INTERVAL = 50;
const BASKET_Y_OFFSET = 80;

function buildFallingFiles(files: File[], canvasWidth: number): FallingFileItem[] {
  return files.map((file, i) => ({
    kind: "file" as const,
    id: `${file.name}-${i}`,
    file,
    x: FILE_HALF_W + Math.random() * (canvasWidth - FILE_HALF_W * 2),
    y: -FILE_HALF_H,
    speed: 2.5 + Math.random() * 3,
    startFrame: i * SPAWN_INTERVAL,
    status: "falling" as const,
  }));
}

function aabbCollision(
  fx: number,
  fy: number,
  bx: number,
  by: number,
): boolean {
  return (
    Math.abs(fx - bx) < BASKET_HALF_WIDTH + FILE_HALF_W &&
    Math.abs(fy - by) < BASKET_HEIGHT / 2 + FILE_HALF_H
  );
}

function drawBasket(
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
  // Rim line above basket opening
  ctx.strokeStyle = "#e879f9";
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.moveTo(x - BASKET_HALF_WIDTH - 6, y - h / 2);
  ctx.lineTo(x + BASKET_HALF_WIDTH + 6, y - h / 2);
  ctx.stroke();
  ctx.restore();
}

function drawFile(
  ctx: CanvasRenderingContext2D,
  ff: FallingFileItem,
  caught: boolean,
): void {
  ctx.save();
  ctx.globalAlpha = caught ? 0.4 : 1;
  const w = FILE_HALF_W * 2;
  const h = FILE_HALF_H * 2;
  const x = ff.x - FILE_HALF_W;
  const y = ff.y - FILE_HALF_H;
  const r = 8;

  ctx.fillStyle = "rgba(30, 27, 75, 0.85)";
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.fill();

  ctx.strokeStyle = caught ? "#6b7280" : "#818cf8";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.stroke();

  ctx.font = "18px sans-serif";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(fileIcon(ff.file), x + 4, ff.y);

  ctx.fillStyle = caught ? "#6b7280" : "#e0e7ff";
  ctx.font = "11px monospace";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText(truncateFilename(ff.file.name, 10), x + 26, y + 4);

  ctx.fillStyle = "#94a3b8";
  ctx.font = "10px monospace";
  ctx.textBaseline = "bottom";
  ctx.fillText(formatSize(ff.file.size), x + 26, y + h - 4);

  ctx.restore();
}

/**
 * Runs the osu!catch game loop on the provided canvas.
 * Returns the game result when all files are resolved, or null while playing.
 */
export function useGameLoop(
  canvasRef: React.RefObject<HTMLCanvasElement | null>,
  basketXRef: React.RefObject<number>,
  files: File[],
  active: boolean,
): FileGameResult | null {
  const [result, setResult] = useState<FileGameResult | null>(null);
  const stateRef = useRef<FallingFileItem[]>([]);
  const frameRef = useRef<number>(0);
  const rafRef = useRef<number>(0);

  const startLoop = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    /* istanbul ignore next */
    if (!ctx) return;

    stateRef.current = buildFallingFiles(files, canvas.width);
    frameRef.current = 0;

    const tick = (): void => {
      const frame = frameRef.current;
      frameRef.current = frame + 1;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
      grad.addColorStop(0, "#0f0c29");
      grad.addColorStop(1, "#302b63");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const basketX = basketXRef.current;
      const basketY = canvas.height - BASKET_Y_OFFSET;

      drawBasket(ctx, basketX, basketY);

      let allDone = true;
      for (const ff of stateRef.current) {
        if (ff.status !== "falling") {
          if (ff.status === "caught") drawFile(ctx, ff, true);
          continue;
        }
        if (frame < ff.startFrame) {
          allDone = false;
          continue;
        }
        allDone = false;
        ff.y += ff.speed;

        if (aabbCollision(ff.x, ff.y, basketX, basketY)) {
          ff.status = "caught";
        } else if (ff.y > canvas.height + FILE_HALF_H) {
          ff.status = "missed";
        } else {
          drawFile(ctx, ff, false);
        }
      }

      if (allDone) {
        const caught = stateRef.current
          .filter((f) => f.status === "caught")
          .map((f) => f.file);
        const missed = stateRef.current
          .filter((f) => f.status === "missed")
          .map((f) => f.file);
        setResult({ caught, missed });
        return;
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
  }, [canvasRef, basketXRef, files]);

  useEffect(() => {
    if (!active) return;
    startLoop();
    return () => { cancelAnimationFrame(rafRef.current); };
  }, [active, startLoop]);

  return result;
}
