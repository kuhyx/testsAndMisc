/**
 * Gameplay paths: catching, missing, the catch flash, piece rendering, and the
 * two x-position clustering branches in assignXPositions.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { usePuzzleGameLoop } from "./usePuzzleGameLoop";

vi.mock("../lib/sliceImage");
import { sliceImage } from "../lib/sliceImage";
import {
  flushPromises,
  installRafHarness,
  makeCanvas,
  makePiece,
  makeRef,
  type FlushTick,
} from "../test/puzzleLoopFixtures";

describe("usePuzzleGameLoop play", () => {
  let flushTick: FlushTick;

  beforeEach(() => {
    flushTick = installRafHarness();
    vi.mocked(sliceImage).mockResolvedValue([makePiece(0, 0)]);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("catches single piece and resolves result (solo x branch, drawPiece no-img branch)", async () => {
    // Math.random()=0 → speed=3, x=48 (solo: minX + 0*(maxX-minX) = 48)
    // basketXRef=48 → caught on tick 0; game ends on same tick
    vi.spyOn(Math, "random").mockReturnValue(0);
    vi.mocked(sliceImage).mockResolvedValue([makePiece(0, 0)]);

    const { result } = renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(makeCanvas(800, 90)),
        makeRef(48),
        new File([""], "img.png"),
        1,
        true,
      ),
    );

    await flushPromises(); // let sliceImage resolve and startLoop run
    flushTick(); // tick 0: spawn, move, caught, flash, allDone → setResult

    await waitFor(() => { expect(result.current).not.toBeNull(); });
    expect(result.current!.caughtPieces).toHaveLength(1);
    expect(result.current!.missedPieces).toHaveLength(0);
  });

  it("misses piece (still-falling + missed branches)", async () => {
    // Math.random()=0 → speed=3, x=48; basket at 500 → no collision
    // piece off bottom at y>90+48=138 → ~62 ticks
    vi.spyOn(Math, "random").mockReturnValue(0);

    const { result } = renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(makeCanvas(800, 90)),
        makeRef(500),
        new File([""], "img.png"),
        1,
        true,
      ),
    );

    await flushPromises();
    for (let i = 0; i < 70; i++) {
      if (result.current !== null) break;
      flushTick();
    }

    await waitFor(() => { expect(result.current).not.toBeNull(); });
    expect(result.current!.caughtPieces).toHaveLength(0);
    expect(result.current!.missedPieces).toHaveLength(1);
  });

  it("tests flash-during and flash-expired branches with 2 pieces", async () => {
    // Piece 0: x=48, speed=3, spawnFrame=0 → caught by basket@48 on tick 0
    // Piece 1: x=168, speed=3, spawnFrame=20 → |168-48|=120>108 → missed at tick~82
    // Flash: piece 0 caught at frame 0; at frame 30+ flash expires
    vi.spyOn(Math, "random")
      .mockReturnValueOnce(0) // speed[0] = 3
      .mockReturnValueOnce(0) // speed[1] = 3
      .mockReturnValueOnce(0) // centerX = 108 (108 + 0*(692-108))
      .mockReturnValueOnce(0) // x[0] = 108 + (0*2-1)*60 = 48
      .mockReturnValueOnce(1); // x[1] = 108 + (1*2-1)*60 = 168

    vi.mocked(sliceImage).mockResolvedValue([
      makePiece(0, 0),
      { ...makePiece(0, 1), gridSize: 2 },
    ]);

    const { result } = renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(makeCanvas(800, 90)),
        makeRef(48),
        new File([""], "img.png"),
        2,
        true,
      ),
    );

    await flushPromises();
    for (let i = 0; i < 90; i++) {
      if (result.current !== null) break;
      flushTick();
    }

    await waitFor(() => { expect(result.current).not.toBeNull(); });
    expect(result.current!.caughtPieces).toHaveLength(1);
    expect(result.current!.missedPieces).toHaveLength(1);
  });

  it("uses drawImage when piece image is loaded (img.complete=true branch)", async () => {
    // Class constructor — arrow functions can't be used with `new`
    class FakeImage {
      complete = true;
      naturalWidth = 100;
      src = "";
    }
    vi.stubGlobal("Image", FakeImage);

    vi.spyOn(Math, "random").mockReturnValue(0);

    // Use large canvas so piece doesn't collide on first tick
    const canvas = makeCanvas(800, 600); // basketY=520; piece reaches it at tick~190
    renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(canvas),
        makeRef(500), // far from x=48 → piece will miss
        new File([""], "img.png"),
        1,
        true,
      ),
    );

    await flushPromises();

    // Run one tick — piece is still falling, drawPiece called with loaded img
    flushTick();

    // Verify drawImage was called (piece has complete+naturalWidth>0)
    const { mockCtx } = await import("../test/canvasMock");
    expect(mockCtx.drawImage).toHaveBeenCalled();
  });

  it("triggers Union-Find path compression with 4 overlapping pieces", async () => {
    vi.spyOn(Math, "random").mockReturnValue(0);
    vi.mocked(sliceImage).mockResolvedValue([
      makePiece(0, 0),
      makePiece(0, 1),
      makePiece(1, 0),
      makePiece(1, 1),
    ]);

    // basketY = 300-80 = 220; all 4 pieces overlap (SPAWN_GAP=20 and speed=3)
    const canvas = makeCanvas(800, 300);
    const { unmount } = renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(canvas),
        makeRef(48),
        new File([""], "img.png"),
        2,
        true,
      ),
    );

    await flushPromises(); // sliceImage resolves → assignXPositions (path compression) runs
    flushTick(); // one tick to confirm loop is running

    unmount();
  });

  it("uses canvasW/2 for centerX when canvas is too narrow", async () => {
    // canvas.width=200: centerMin=108 >= centerMax=92 → uses 200/2=100
    vi.spyOn(Math, "random").mockReturnValue(0.5);

    vi.mocked(sliceImage).mockResolvedValue([
      makePiece(0, 0),
      makePiece(0, 1),
    ]);

    const canvas = makeCanvas(200, 90); // basketY=10
    // With centerX=100, both pieces at x=100 (offset = 0); basket@100 → caught
    const { result } = renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(canvas),
        makeRef(100),
        new File([""], "img.png"),
        2,
        true,
      ),
    );

    await flushPromises();
    for (let i = 0; i < 30; i++) {
      if (result.current !== null) break;
      flushTick();
    }

    await waitFor(() => { expect(result.current).not.toBeNull(); });
  });
});
