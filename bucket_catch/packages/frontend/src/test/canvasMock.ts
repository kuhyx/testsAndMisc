import { vi } from "vitest";

export const mockGradient = { addColorStop: vi.fn() };

export const mockCtx = {
  clearRect: vi.fn(),
  fillRect: vi.fn(),
  strokeRect: vi.fn(),
  drawImage: vi.fn(),
  fillText: vi.fn(),
  measureText: vi.fn(() => ({ width: 0 })),
  save: vi.fn(),
  restore: vi.fn(),
  beginPath: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  stroke: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  roundRect: vi.fn(),
  createLinearGradient: vi.fn(() => mockGradient),
  fillStyle: "" as string | CanvasGradient | CanvasPattern,
  strokeStyle: "" as string | CanvasGradient | CanvasPattern,
  lineWidth: 1,
  lineJoin: "miter" as CanvasLineJoin,
  font: "",
  textAlign: "start" as CanvasTextAlign,
  textBaseline: "alphabetic" as CanvasTextBaseline,
  globalAlpha: 1,
};
