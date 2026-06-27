import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { GameCanvas } from "./GameCanvas";

vi.mock("../hooks/useBasketControl", () => ({
  useBasketControl: vi.fn(() => ({ current: 400 })),
}));
vi.mock("../hooks/useGameLoop", () => ({
  useGameLoop: vi.fn(() => null),
}));

import { useGameLoop } from "../hooks/useGameLoop";

describe("GameCanvas", () => {
  beforeEach(() => {
    vi.mocked(useGameLoop).mockReturnValue(null);
  });

  it("renders a canvas element and hint text", () => {
    const { container } = render(
      <GameCanvas files={[]} onDone={() => undefined} />,
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
      <GameCanvas files={[]} onDone={() => undefined} />,
    );

    expect(addSpy).toHaveBeenCalledWith("resize", expect.any(Function));
    unmount();
    expect(removeSpy).toHaveBeenCalledWith("resize", expect.any(Function));
  });

  it("calls onDone with the result when useGameLoop returns non-null", async () => {
    const result = { caught: [], missed: [] };
    vi.mocked(useGameLoop).mockReturnValue(result);

    const onDone = vi.fn();
    render(<GameCanvas files={[]} onDone={onDone} />);

    await waitFor(() => {
      expect(onDone).toHaveBeenCalledWith(result);
    });
  });

  it("does not call onDone when result is null", () => {
    vi.mocked(useGameLoop).mockReturnValue(null);
    const onDone = vi.fn();
    render(<GameCanvas files={[]} onDone={onDone} />);
    expect(onDone).not.toHaveBeenCalled();
  });

  it("resize handler returns safely when canvasRef is null after unmount", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const { unmount } = render(<GameCanvas files={[]} onDone={() => undefined} />);

    const resizeArgs = addSpy.mock.calls.find((c) => c[0] === "resize");
    const resize = resizeArgs?.[1];

    unmount(); // React nulls canvasRef.current

    // Call the captured handler — canvas is now null → covers the null-guard branch
    if (typeof resize === "function") resize(new Event("resize"));

    addSpy.mockRestore();
  });
});
