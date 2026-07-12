import "@testing-library/jest-dom";
import { vi, beforeEach } from "vitest";

beforeEach(() => {
  vi.clearAllMocks();
});

// jsdom lacks object-URL support; several flows touch it.
URL.createObjectURL = vi.fn(() => "blob:mock");
URL.revokeObjectURL = vi.fn();
