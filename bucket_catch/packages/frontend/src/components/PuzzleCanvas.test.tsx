import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { PuzzleCanvas } from "./PuzzleCanvas";

vi.mock("../hooks/useBasketControl", () => ({
  useBasketControl: vi.fn(() => ({ current: 400 })),
}));
vi.mock("../hooks/usePuzzleGameLoop", () => ({
  usePuzzleGameLoop: vi.fn(() => null),
}));

import { usePuzzleGameLoop } from "../hooks/usePuzzleGameLoop";

const imageFile = new File(["img"], "test.png", { type: "image/png" });

describe("PuzzleCanvas", () => {
  beforeEach(() => {
    vi.mocked(usePuzzleGameLoop).mockReturnValue(null);
  });

  it("renders a canvas element and puzzle hint text", () => {
    const { container } = render(
      <PuzzleCanvas imageFile={imageFile} gridSize={2} onDone={() => undefined} />,
    );
    expect(container.querySelector("canvas")).toBeInTheDocument();
    expect(
      container.querySelector(".hint") ??
        container.querySelector('[class*="hint"]'),
    ).toBeInTheDocument();
  });

  it("adds resize event listener on mount and removes it on unmount", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const removeSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = render(
      <PuzzleCanvas imageFile={imageFile} gridSize={2} onDone={() => undefined} />,
    );

    expect(addSpy).toHaveBeenCalledWith("resize", expect.any(Function));
    unmount();
    expect(removeSpy).toHaveBeenCalledWith("resize", expect.any(Function));
  });

  it("calls onDone with the result when usePuzzleGameLoop returns non-null", async () => {
    const result = { caughtPieces: [], missedPieces: [], gridSize: 2 };
    vi.mocked(usePuzzleGameLoop).mockReturnValue(result);

    const onDone = vi.fn();
    render(<PuzzleCanvas imageFile={imageFile} gridSize={2} onDone={onDone} />);

    await waitFor(() => {
      expect(onDone).toHaveBeenCalledWith(result);
    });
  });

  it("does not call onDone when result is null", () => {
    vi.mocked(usePuzzleGameLoop).mockReturnValue(null);
    const onDone = vi.fn();
    render(<PuzzleCanvas imageFile={imageFile} gridSize={2} onDone={onDone} />);
    expect(onDone).not.toHaveBeenCalled();
  });

  it("resize handler returns safely when canvasRef is null after unmount", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const { unmount } = render(
      <PuzzleCanvas imageFile={imageFile} gridSize={2} onDone={() => undefined} />,
    );

    const resizeArgs = addSpy.mock.calls.find((c) => c[0] === "resize");
    const resize = resizeArgs?.[1];

    unmount(); // React nulls canvasRef.current

    if (typeof resize === "function") resize(new Event("resize"));

    addSpy.mockRestore();
  });
});
