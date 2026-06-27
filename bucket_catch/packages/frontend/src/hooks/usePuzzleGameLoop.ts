import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import type { FallingPuzzleItem, PuzzlePiece, PuzzleGameResult } from "../types";
import { sliceImage } from "../lib/sliceImage";

const BASKET_HALF_WIDTH = 60;
const BASKET_HEIGHT = 40;
const PIECE_HALF_W = 48;
const PIECE_HALF_H = 48;
const BASKET_Y_OFFSET = 80;
const MIN_SPEED = 3;
const SPEED_RANGE = 3;
/** y-half-extent of the catch zone: BASKET_HEIGHT/2 + PIECE_HALF_H */
const CATCH_HALF = BASKET_HEIGHT / 2 + PIECE_HALF_H; // 68 px
/** x-half-extent: basket catches a piece within this horizontal distance */
const CATCH_RANGE = BASKET_HALF_WIDTH + PIECE_HALF_W; // 108 px
/** Frames between consecutive piece spawn times — controls pacing. */
const SPAWN_GAP = 20;

interface ScheduledPiece {
  piece: PuzzlePiece;
  spawnFrame: number;
  speed: number;
  x: number;
}

/**
 * Computes when each piece enters/exits the catch zone, groups pieces
 * whose windows overlap (Union-Find), and assigns x positions so that
 * every group fits within one basket-width — guaranteeing 100% is achievable.
 */
function assignXPositions(
  scheduled: ScheduledPiece[],
  basketY: number,
  canvasW: number,
): void {
  const n = scheduled.length;
  const parent = Array.from({ length: n }, (_, i) => i);

  const find = (start: number): number => {
    let root = start;
    while (parent[root] !== root) root = parent[root];
    let i = start;
    while (parent[i] !== root) {
      const next = parent[i];
      parent[i] = root;
      i = next;
    }
    return root;
  };

  const union = (a: number, b: number): void => {
    parent[find(a)] = find(b);
  };

  // Catch window for each piece: the frame range when it's at basket height.
  const enters = scheduled.map(
    (s) => s.spawnFrame + (basketY - CATCH_HALF + PIECE_HALF_H) / s.speed,
  );
  const exits = scheduled.map(
    (s) => s.spawnFrame + (basketY + CATCH_HALF + PIECE_HALF_H) / s.speed,
  );

  // Union all pairs whose windows overlap — they arrive simultaneously.
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (enters[i] <= exits[j] && enters[j] <= exits[i]) {
        union(i, j);
      }
    }
  }

  // Collect groups.
  const groups = new Map<number, number[]>();
  for (let i = 0; i < n; i++) {
    const root = find(i);
    const g = groups.get(root);
    if (g !== undefined) {
      g.push(i);
    } else {
      groups.set(root, [i]);
    }
  }

  // maxOffset: pieces within ±maxOffset of cluster center are all reachable
  // from a single basket position (|piece.x - basketX| < CATCH_RANGE iff
  // basketX = centerX and |piece.x - centerX| ≤ maxOffset < CATCH_RANGE).
  const maxOffset = BASKET_HALF_WIDTH; // 60 px
  const minX = PIECE_HALF_W;
  const maxX = canvasW - PIECE_HALF_W;

  for (const indices of groups.values()) {
    if (indices.length === 1) {
      // Solo piece: any position across the full canvas width.
      scheduled[indices[0]].x = minX + Math.random() * (maxX - minX);
    } else {
      // Multi-piece group: cluster within ±maxOffset of a shared center.
      const centerMin = PIECE_HALF_W + maxOffset;
      const centerMax = canvasW - PIECE_HALF_W - maxOffset;
      const centerX =
        centerMin < centerMax
          ? centerMin + Math.random() * (centerMax - centerMin)
          : canvasW / 2;
      for (const idx of indices) {
        scheduled[idx].x =
          centerX + (Math.random() * 2 - 1) * maxOffset;
      }
    }
  }
}

function aabbCollision(
  fx: number,
  fy: number,
  bx: number,
  by: number,
): boolean {
  return (
    Math.abs(fx - bx) < CATCH_RANGE &&
    Math.abs(fy - by) < BASKET_HEIGHT / 2 + PIECE_HALF_H
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
  ctx.strokeStyle = "#e879f9";
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.moveTo(x - BASKET_HALF_WIDTH - 6, y - h / 2);
  ctx.lineTo(x + BASKET_HALF_WIDTH + 6, y - h / 2);
  ctx.stroke();
  ctx.restore();
}

function drawPiece(
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

function drawHUD(
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

/**
 * Puzzle game loop.
 *
 * All pieces are scheduled up-front. Their x positions are assigned via
 * interval-graph clustering so that pieces arriving simultaneously share a
 * spatial cluster the basket can cover in one position — guaranteeing 100%
 * is always achievable. Multiple pieces fall simultaneously, creating an
 * exciting hectic visual while remaining fair.
 */
export function usePuzzleGameLoop(
  canvasRef: RefObject<HTMLCanvasElement | null>,
  basketXRef: RefObject<number>,
  imageFile: File,
  gridSize: number,
  active: boolean,
): PuzzleGameResult | null {
  const [result, setResult] = useState<PuzzleGameResult | null>(null);
  const scheduleRef = useRef<ScheduledPiece[]>([]);
  const activeItemsRef = useRef<FallingPuzzleItem[]>([]);
  const resolvedRef = useRef<FallingPuzzleItem[]>([]);
  const resolvedFrameMapRef = useRef<Map<string, number>>(new Map());
  const frameRef = useRef<number>(0);
  const rafRef = useRef<number>(0);
  const imgsRef = useRef<Map<string, HTMLImageElement>>(new Map());
  const totalRef = useRef<number>(0);

  const startLoop = useCallback(
    (pieces: PuzzlePiece[], canvas: HTMLCanvasElement) => {
      const ctx = canvas.getContext("2d");
      /* istanbul ignore next */
      if (!ctx) return;

      const basketY = canvas.height - BASKET_Y_OFFSET;

      // Build schedule: staggered spawn times, random speeds.
      const scheduled: ScheduledPiece[] = pieces.map((piece, i) => ({
        piece,
        spawnFrame: i * SPAWN_GAP,
        speed: MIN_SPEED + Math.random() * SPEED_RANGE,
        x: 0, // will be filled by assignXPositions
      }));

      // Assign x positions with the spatial clustering guarantee.
      assignXPositions(scheduled, basketY, canvas.width);

      // Sort by spawn time (speeds vary, so original order isn't strictly sorted).
      scheduled.sort((a, b) => a.spawnFrame - b.spawnFrame);

      scheduleRef.current = scheduled;
      activeItemsRef.current = [];
      resolvedRef.current = [];
      resolvedFrameMapRef.current = new Map();
      frameRef.current = 0;
      totalRef.current = pieces.length;

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
        drawBasket(ctx, basketX, basketY);

        // Spawn pieces whose time has come.
        while (
          scheduleRef.current.length > 0 &&
          frame >= scheduleRef.current[0].spawnFrame
        ) {
          // while condition guarantees length > 0, so shift() is always defined
          const s = scheduleRef.current.shift()!;
          activeItemsRef.current.push({
            kind: "puzzle",
            id: `puzzle-${s.piece.row}-${s.piece.col}`,
            piece: s.piece,
            x: s.x,
            y: -PIECE_HALF_H,
            speed: s.speed,
            startFrame: frame,
            status: "falling",
          });
        }

        // Update all falling pieces.
        const stillActive: FallingPuzzleItem[] = [];
        for (const item of activeItemsRef.current) {
          const img = imgsRef.current.get(`${item.piece.row}-${item.piece.col}`);
          item.y += item.speed;

          if (aabbCollision(item.x, item.y, basketX, basketY)) {
            item.status = "caught";
            resolvedRef.current.push(item);
            resolvedFrameMapRef.current.set(item.id, frame);
          } else if (item.y > canvas.height + PIECE_HALF_H) {
            item.status = "missed";
            resolvedRef.current.push(item);
            resolvedFrameMapRef.current.set(item.id, frame);
          } else {
            drawPiece(ctx, item, img, false);
            stillActive.push(item);
          }
        }
        activeItemsRef.current = stillActive;

        // Flash caught pieces briefly at their catch position.
        for (const item of resolvedRef.current) {
          if (item.status === "caught") {
            // id is always set in the map when piece is resolved (lines above)
            const rf = resolvedFrameMapRef.current.get(item.id)!;
            if (frame - rf < 30) {
              const img = imgsRef.current.get(
                `${item.piece.row}-${item.piece.col}`,
              );
              drawPiece(ctx, item, img, true);
            }
          }
        }

        const caughtCount = resolvedRef.current.filter(
          (p) => p.status === "caught",
        ).length;
        drawHUD(
          ctx,
          canvas,
          caughtCount,
          totalRef.current,
          resolvedRef.current.length,
        );

        if (
          activeItemsRef.current.length === 0 &&
          scheduleRef.current.length === 0
        ) {
          const caught = resolvedRef.current.filter(
            (p) => p.status === "caught",
          );
          const missed = resolvedRef.current.filter(
            (p) => p.status === "missed",
          );
          setResult({ caughtPieces: caught, missedPieces: missed, gridSize });
          return;
        }

        rafRef.current = requestAnimationFrame(tick);
      };

      rafRef.current = requestAnimationFrame(tick);
    },
    [basketXRef, gridSize],
  );

  useEffect(() => {
    if (!active) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    let cancelled = false;

    void sliceImage(imageFile, gridSize).then((pieces) => {
      if (cancelled) return;
      pieces.forEach((piece) => {
        const img = new Image();
        img.src = piece.imageUrl;
        imgsRef.current.set(`${piece.row}-${piece.col}`, img);
      });
      startLoop(pieces, canvas);
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafRef.current);
    };
  }, [active, imageFile, gridSize, canvasRef, startLoop]);

  return result;
}
