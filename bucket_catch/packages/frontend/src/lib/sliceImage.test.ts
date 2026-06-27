import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { sliceImage } from "./sliceImage";

// Captures the last Image instance created so tests can trigger onload/onerror.
let capturedImg: {
  onload: (() => void) | null;
  onerror: (() => void) | null;
  src: string;
  width: number;
  height: number;
};

class FakeImage {
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  src = "";
  width = 200;
  height = 100;
  constructor() {
    capturedImg = this;
  }
}

describe("sliceImage", () => {
  beforeEach(() => {
    vi.stubGlobal("Image", FakeImage);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("resolves with pieces when image loads", async () => {
    const file = new File([""], "img.png", { type: "image/png" });
    const promise = sliceImage(file, 2);

    // Trigger onload synchronously — sliceImage has already assigned it.
    capturedImg.onload?.();

    const pieces = await promise;
    expect(pieces).toHaveLength(4); // 2×2 grid
    expect(pieces[0]).toMatchObject({ row: 0, col: 0, gridSize: 2 });
    expect(pieces[3]).toMatchObject({ row: 1, col: 1, gridSize: 2 });
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock");
  });

  it("includes pieceWidth and pieceHeight from image dimensions", async () => {
    const file = new File([""], "img.png");
    const promise = sliceImage(file, 2);
    capturedImg.onload?.();
    const pieces = await promise;
    // FakeImage.width=200, height=100, gridSize=2 → pieceWidth=100, pieceHeight=50
    expect(pieces[0].pieceWidth).toBe(100);
    expect(pieces[0].pieceHeight).toBe(50);
  });

  it("resolves with 1 piece for 1×1 grid", async () => {
    const file = new File([""], "img.png");
    const promise = sliceImage(file, 1);
    capturedImg.onload?.();
    const pieces = await promise;
    expect(pieces).toHaveLength(1);
  });

  it("rejects when offscreen canvas getContext returns null", async () => {
    // Save and override the prototype mock to return null for this test only
    const savedImpl = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = (() => null) as typeof HTMLCanvasElement.prototype.getContext;

    const file = new File([""], "img.png");
    const promise = sliceImage(file, 1);
    capturedImg.onload?.();
    await expect(promise).rejects.toThrow("Canvas 2D context not available");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock");

    // Restore so subsequent tests in this file have the mock context
    HTMLCanvasElement.prototype.getContext = savedImpl;
  });

  it("rejects when image fails to load", async () => {
    const file = new File([""], "broken.jpg");
    const promise = sliceImage(file, 2);
    capturedImg.onerror?.();
    await expect(promise).rejects.toThrow("Failed to load image for slicing");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock");
  });
});
