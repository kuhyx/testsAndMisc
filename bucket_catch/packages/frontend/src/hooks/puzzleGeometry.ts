import type { PuzzlePiece } from "../types";

/**
 * Board geometry and piece scheduling for the puzzle game.
 *
 * The interesting part is `assignXPositions`, which is what makes a 100% score
 * always achievable: pieces that arrive at the basket at overlapping times are
 * clustered so one basket position covers all of them.
 */

export const BASKET_HALF_WIDTH = 60;
export const BASKET_HEIGHT = 40;
export const PIECE_HALF_W = 48;
export const PIECE_HALF_H = 48;
export const BASKET_Y_OFFSET = 80;
export const MIN_SPEED = 3;
export const SPEED_RANGE = 3;
/** y-half-extent of the catch zone: BASKET_HEIGHT/2 + PIECE_HALF_H */
export const CATCH_HALF = BASKET_HEIGHT / 2 + PIECE_HALF_H; // 68 px
/** x-half-extent: basket catches a piece within this horizontal distance */
export const CATCH_RANGE = BASKET_HALF_WIDTH + PIECE_HALF_W; // 108 px
/** Frames between consecutive piece spawn times — controls pacing. */
export const SPAWN_GAP = 20;

export interface ScheduledPiece {
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
export function assignXPositions(
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

export function aabbCollision(
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
