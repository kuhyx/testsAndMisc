import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import type { FallingPuzzleItem, PuzzlePiece, PuzzleGameResult } from "../types";
import { sliceImage } from "../lib/sliceImage";
import {
  BASKET_Y_OFFSET,
  MIN_SPEED,
  PIECE_HALF_H,
  SPAWN_GAP,
  SPEED_RANGE,
  aabbCollision,
  assignXPositions,
  type ScheduledPiece,
} from "./puzzleGeometry";
import { drawBackdrop, drawBasket, drawHUD, drawPiece } from "./puzzleRender";

/**
 * Puzzle game loop.
 *
 * All pieces are scheduled up-front. Their x positions are assigned via
 * interval-graph clustering so that pieces arriving simultaneously share a
 * spatial cluster the basket can cover in one position — guaranteeing 100%
 * is always achievable. Multiple pieces fall simultaneously, creating an
 * exciting hectic visual while remaining fair.
 *
 * The clustering itself lives in `puzzleGeometry.ts` and the canvas drawing in
 * `puzzleRender.ts`; what remains here is the per-frame tick.
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

        drawBackdrop(ctx, canvas);

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
