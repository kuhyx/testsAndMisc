/** Lifecycle and guard paths: when the loop declines to start, and teardown. */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { PuzzlePiece } from "../types";
import { usePuzzleGameLoop } from "./usePuzzleGameLoop";

vi.mock("../lib/sliceImage");
import { sliceImage } from "../lib/sliceImage";
import {
  flushPromises,
  installRafHarness,
  makeCanvas,
  makePiece,
  makeRef,
} from "../test/puzzleLoopFixtures";

describe("usePuzzleGameLoop lifecycle", () => {
  beforeEach(() => {
    installRafHarness();
    vi.mocked(sliceImage).mockResolvedValue([makePiece(0, 0)]);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("returns null when active=false", () => {
    const { result } = renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(makeCanvas()),
        makeRef(400),
        new File([""], "img.png"),
        1,
        false,
      ),
    );
    expect(result.current).toBeNull();
    expect(sliceImage).not.toHaveBeenCalled();
  });

  it("returns null when canvas is null", async () => {
    const { result } = renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(null),
        makeRef(400),
        new File([""], "img.png"),
        1,
        true,
      ),
    );
    await flushPromises();
    expect(result.current).toBeNull();
    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it("does nothing when unmounted before sliceImage resolves (cancelled branch)", async () => {
    let resolveSlice!: (pieces: PuzzlePiece[]) => void;
    vi.mocked(sliceImage).mockReturnValue(
      new Promise((res) => { resolveSlice = res; }),
    );

    const { unmount } = renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(makeCanvas()),
        makeRef(400),
        new File([""], "img.png"),
        1,
        true,
      ),
    );

    unmount(); // sets cancelled=true before sliceImage resolves
    await act(async () => {
      resolveSlice([makePiece(0, 0)]);
      await Promise.resolve();
    });

    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it("cancels RAF on unmount after game started", async () => {
    vi.spyOn(Math, "random").mockReturnValue(0);

    const { unmount } = renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(makeCanvas()),
        makeRef(400),
        new File([""], "img.png"),
        1,
        true,
      ),
    );

    await flushPromises();
    unmount();
    expect(cancelAnimationFrame).toHaveBeenCalled();
  });

  it("does not start RAF when startLoop canvas.getContext returns null", async () => {
    // A plain fake canvas whose getContext returns null avoids prototype contamination
    const fakeCanvas = {
      width: 800,
      height: 300,
      clientWidth: 800,
      clientHeight: 300,
      getContext: () => null,
    } as unknown as HTMLCanvasElement;

    renderHook(() =>
      usePuzzleGameLoop(
        makeRef<HTMLCanvasElement | null>(fakeCanvas),
        makeRef(400),
        new File([""], "img.png"),
        1,
        true,
      ),
    );

    await flushPromises(); // sliceImage resolves → startLoop called → null ctx → early return

    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });
});
