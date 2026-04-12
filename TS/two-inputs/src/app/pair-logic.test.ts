import { describe, it, expect, vi } from "vitest";
import { findValidPairs, findCorrespondingValue, changeIndex } from "./pair-logic";

describe("findValidPairs", () => {
  it("returns null when any argument is null", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(findValidPairs(null, 100, 250, 325)).toBeNull();
    expect(findValidPairs(25, null, 250, 325)).toBeNull();
    expect(findValidPairs(25, 100, null, 325)).toBeNull();
    expect(findValidPairs(25, 100, 250, null)).toBeNull();
    expect(spy).toHaveBeenCalledTimes(4);
    spy.mockRestore();
  });

  it("returns valid pairs for step=25, min=100, max=250, target=325", () => {
    const result = findValidPairs(25, 100, 250, 325);
    expect(result).toEqual([
      [100, 225],
      [125, 200],
      [150, 175],
      [175, 150],
      [200, 125],
      [225, 100],
    ]);
  });

  it("returns empty array when no valid pairs exist", () => {
    const result = findValidPairs(25, 200, 250, 325);
    expect(result).toEqual([]);
  });

  it("returns symmetric pairs", () => {
    const result = findValidPairs(50, 100, 200, 300);
    expect(result).toEqual([
      [100, 200],
      [150, 150],
      [200, 100],
    ]);
  });

  it("handles case where n2 is not a multiple of step", () => {
    const result = findValidPairs(30, 100, 250, 325);
    expect(result).toEqual([]);
  });
});

describe("findCorrespondingValue", () => {
  const pairs: Array<[number, number]> = [
    [100, 225],
    [125, 200],
    [150, 175],
  ];

  it("returns match on first element", () => {
    expect(findCorrespondingValue(pairs, 100)).toEqual([225, 0]);
    expect(findCorrespondingValue(pairs, 125)).toEqual([200, 1]);
  });

  it("returns match on second element", () => {
    expect(findCorrespondingValue(pairs, 225)).toEqual([100, 0]);
    expect(findCorrespondingValue(pairs, 200)).toEqual([125, 1]);
  });

  it("returns null when no match found", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(findCorrespondingValue(pairs, 999)).toBeNull();
    expect(spy).toHaveBeenCalledTimes(1);
    spy.mockRestore();
  });
});

describe("changeIndex", () => {
  it("wraps forward past end", () => {
    expect(changeIndex(4, true, 5)).toBe(0);
  });

  it("increments normally forward", () => {
    expect(changeIndex(2, true, 5)).toBe(3);
  });

  it("wraps backward past start", () => {
    expect(changeIndex(0, false, 5)).toBe(4);
  });

  it("decrements normally backward", () => {
    expect(changeIndex(3, false, 5)).toBe(2);
  });

  it("returns currentValue when length is undefined", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(changeIndex(3, true, undefined)).toBe(3);
    expect(spy).toHaveBeenCalledTimes(1);
    spy.mockRestore();
  });
});
