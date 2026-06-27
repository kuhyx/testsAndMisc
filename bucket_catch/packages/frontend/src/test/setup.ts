import "@testing-library/jest-dom";
import { vi, beforeEach } from "vitest";
import { mockCtx } from "./canvasMock";

beforeEach(() => {
  vi.clearAllMocks();
});

HTMLCanvasElement.prototype.getContext = vi.fn(
  () => mockCtx,
) as unknown as typeof HTMLCanvasElement.prototype.getContext;

HTMLCanvasElement.prototype.toDataURL = vi.fn(
  () => "data:image/png;base64,mock",
);
