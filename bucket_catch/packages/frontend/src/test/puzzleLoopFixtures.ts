import { act } from "@testing-library/react";
import type React from "react";
import type { PuzzlePiece } from "../types";

/**
 * Shared fixtures for the usePuzzleGameLoop tests.
 *
 * Lives under src/test/ because the coverage config excludes that path — a
 * fixture placed beside the hook would be counted as production code and break
 * the 100% gate.
 */

export const makeRef = <T>(val: T): React.RefObject<T> => ({
  current: val,
});

export const makePiece = (row: number, col: number): PuzzlePiece => ({
  row,
  col,
  gridSize: 1,
  imageUrl: "data:image/png;base64,mock",
  pieceWidth: 50,
  pieceHeight: 50,
});

export const makeCanvas = (w = 800, h = 90): HTMLCanvasElement => {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c;
};

/** Drives one queued animation frame, if any is pending. */
export type FlushTick = () => void;

/**
 * Installs the requestAnimationFrame harness the loop tests drive by hand.
 *
 * Returns a `flushTick` bound to this suite's own queue, so each describe block
 * gets an isolated set of callbacks rather than sharing module state.
 *
 * @returns A function that runs the most recently queued frame.
 */
export function installRafHarness(): FlushTick {
  const rafCallbacks: FrameRequestCallback[] = [];
  vi.stubGlobal(
    "requestAnimationFrame",
    vi.fn((cb: FrameRequestCallback) => {
      rafCallbacks.push(cb);
      return rafCallbacks.length;
    }),
  );
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
  return () => {
    const cb = rafCallbacks.pop();
    if (cb) act(() => { cb(0); });
  };
}

/** Lets pending promise callbacks settle inside act(). */
export const flushPromises = async (): Promise<void> => {
  await act(async () => { await Promise.resolve(); });
};
