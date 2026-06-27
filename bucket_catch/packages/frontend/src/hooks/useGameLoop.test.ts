import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type React from "react";
import { useGameLoop } from "./useGameLoop";

const makeRef = <T>(val: T): React.RefObject<T> =>
  ({ current: val }) as React.RefObject<T>;

describe("useGameLoop", () => {
  let rafCallbacks: FrameRequestCallback[];

  beforeEach(() => {
    rafCallbacks = [];
    vi.stubGlobal(
      "requestAnimationFrame",
      vi.fn((cb: FrameRequestCallback) => {
        rafCallbacks.push(cb);
        return rafCallbacks.length;
      }),
    );
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  const flushTick = (): void => {
    const cb = rafCallbacks.pop();
    if (cb) act(() => { cb(0); });
  };

  it("returns null when active=false and does not start RAF", () => {
    const { result } = renderHook(() =>
      useGameLoop(
        makeRef<HTMLCanvasElement | null>(null),
        makeRef(400),
        [],
        false,
      ),
    );
    expect(result.current).toBeNull();
    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it("returns null when canvasRef.current is null (active=true)", () => {
    renderHook(() =>
      useGameLoop(
        makeRef<HTMLCanvasElement | null>(null),
        makeRef(400),
        [new File(["x"], "a.txt")],
        true,
      ),
    );
    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it("cancels RAF on unmount", () => {
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 600;
    const { unmount } = renderHook(() =>
      useGameLoop(
        makeRef<HTMLCanvasElement | null>(canvas),
        makeRef(400),
        [],
        true,
      ),
    );
    unmount();
    expect(cancelAnimationFrame).toHaveBeenCalled();
  });

  it("resolves immediately with empty result when files is empty", async () => {
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 600;

    const { result } = renderHook(() =>
      useGameLoop(
        makeRef<HTMLCanvasElement | null>(canvas),
        makeRef(400),
        [],
        true,
      ),
    );

    flushTick(); // allDone=true on first frame → setResult
    await waitFor(() => { expect(result.current).not.toBeNull(); });
    expect(result.current!.caught).toHaveLength(0);
    expect(result.current!.missed).toHaveLength(0);
  });

  it("catches file and resolves result (caught branch + caught-draw branch)", async () => {
    // Math.random()=0 → file x=48, speed=2.5
    // basketXRef=48 → |fx-bx|=0<108, |fy-by|=35.5<48 → caught on tick 0
    vi.spyOn(Math, "random").mockReturnValue(0);

    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 90; // basketY = 90-80 = 10

    const { result } = renderHook(() =>
      useGameLoop(
        makeRef<HTMLCanvasElement | null>(canvas),
        makeRef(48),
        [new File(["x"], "a.txt")],
        true,
      ),
    );

    flushTick(); // tick 0: caught
    flushTick(); // tick 1: draw caught + allDone=true → setResult

    await waitFor(() => { expect(result.current).not.toBeNull(); });
    expect(result.current!.caught).toHaveLength(1);
    expect(result.current!.missed).toHaveLength(0);
  });

  it("misses file (still-falling + missed branches)", async () => {
    // Math.random()=0 → file x=48, speed=2.5; basketXRef=400
    // |48-400|=352 > 108 → no collision; off-bottom at y>118, ~60 ticks
    vi.spyOn(Math, "random").mockReturnValue(0);

    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 90;

    const { result } = renderHook(() =>
      useGameLoop(
        makeRef<HTMLCanvasElement | null>(canvas),
        makeRef(400),
        [new File(["x"], "a.txt")],
        true,
      ),
    );

    for (let i = 0; i < 65; i++) {
      if (result.current !== null) break;
      flushTick();
    }

    await waitFor(() => { expect(result.current).not.toBeNull(); });
    expect(result.current!.caught).toHaveLength(0);
    expect(result.current!.missed).toHaveLength(1);
  });

  it("does not start RAF when canvas.getContext returns null", () => {
    // A plain fake canvas whose getContext returns null avoids prototype contamination
    const fakeCanvas = {
      width: 800,
      height: 600,
      clientWidth: 800,
      clientHeight: 600,
      getContext: () => null,
    } as unknown as HTMLCanvasElement;

    renderHook(() =>
      useGameLoop(makeRef<HTMLCanvasElement | null>(fakeCanvas), makeRef(400), [], true),
    );

    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it("handles not-yet-spawned branch with two files (startFrames 0 and 50)", async () => {
    // Both files: x=48, speed=2.5; basket at 48 → both caught
    // File 1 has startFrame=50 → "frame < ff.startFrame" branch hit for ticks 1-49
    vi.spyOn(Math, "random").mockReturnValue(0);

    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 90;

    const { result } = renderHook(() =>
      useGameLoop(
        makeRef<HTMLCanvasElement | null>(canvas),
        makeRef(48),
        [new File(["a"], "a.txt"), new File(["b"], "b.txt")],
        true,
      ),
    );

    for (let i = 0; i < 60; i++) {
      if (result.current !== null) break;
      flushTick();
    }

    await waitFor(() => { expect(result.current).not.toBeNull(); });
    expect(result.current!.caught).toHaveLength(2);
    expect(result.current!.missed).toHaveLength(0);
  });
});
