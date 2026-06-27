import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import type React from "react";
import { useBasketControl } from "./useBasketControl";

const makeRef = <T>(val: T): React.RefObject<T> =>
  ({ current: val }) as React.RefObject<T>;

describe("useBasketControl", () => {
  it("initialises basket x to half of window.innerWidth", () => {
    const { result } = renderHook(() =>
      useBasketControl(makeRef<HTMLCanvasElement | null>(null)),
    );
    expect(result.current.current).toBe(window.innerWidth / 2);
  });

  it("does not attach listener when canvas is null", () => {
    const canvasRef = makeRef<HTMLCanvasElement | null>(null);
    // If the effect returned early (canvas null), no error and value unchanged.
    const { result } = renderHook(() => useBasketControl(canvasRef));
    expect(result.current.current).toBe(window.innerWidth / 2);
  });

  it("updates basket x on mouse move within canvas", () => {
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.getBoundingClientRect = () =>
      ({ left: 0, top: 0 }) as DOMRect;

    const { result } = renderHook(() =>
      useBasketControl(makeRef<HTMLCanvasElement | null>(canvas)),
    );

    fireEvent.mouseMove(canvas, { clientX: 400 });
    expect(result.current.current).toBe(400);
  });

  it("clamps basket x to minimum (BASKET_HALF_WIDTH = 60)", () => {
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.getBoundingClientRect = () => ({ left: 0 }) as DOMRect;

    const { result } = renderHook(() =>
      useBasketControl(makeRef<HTMLCanvasElement | null>(canvas)),
    );

    fireEvent.mouseMove(canvas, { clientX: 5 }); // x = 5 < 60
    expect(result.current.current).toBe(60);
  });

  it("clamps basket x to maximum (canvas.width - 60)", () => {
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.getBoundingClientRect = () => ({ left: 0 }) as DOMRect;

    const { result } = renderHook(() =>
      useBasketControl(makeRef<HTMLCanvasElement | null>(canvas)),
    );

    fireEvent.mouseMove(canvas, { clientX: 790 }); // x = 790 > 800 - 60 = 740
    expect(result.current.current).toBe(740);
  });

  it("removes event listener on unmount", () => {
    const canvas = document.createElement("canvas");
    canvas.width = 200;
    canvas.getBoundingClientRect = () => ({ left: 0 }) as DOMRect;
    const removeSpy = vi.spyOn(canvas, "removeEventListener");

    const { unmount } = renderHook(() =>
      useBasketControl(makeRef<HTMLCanvasElement | null>(canvas)),
    );

    unmount();
    expect(removeSpy).toHaveBeenCalledWith("mousemove", expect.any(Function));
  });
});
