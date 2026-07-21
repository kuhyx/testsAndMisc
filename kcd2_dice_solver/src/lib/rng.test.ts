import { describe, expect, it } from "vitest";
import { mulberry32, randomInt } from "./rng.ts";

describe("mulberry32", () => {
  it("is deterministic for a given seed", () => {
    const a = mulberry32(42);
    const b = mulberry32(42);
    const first = [a(), a(), a()];
    const second = [b(), b(), b()];
    expect(first).toEqual(second);
  });

  it("produces different streams for different seeds", () => {
    expect(mulberry32(1)()).not.toBe(mulberry32(2)());
  });

  it("stays within [0, 1)", () => {
    const random = mulberry32(7);
    for (let i = 0; i < 1000; i += 1) {
      const value = random();
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThan(1);
    }
  });
});

describe("randomInt", () => {
  it("stays within the requested bound", () => {
    const random = mulberry32(99);
    const seen = new Set<number>();
    for (let i = 0; i < 500; i += 1) {
      const value = randomInt(random, 5);
      expect(Number.isInteger(value)).toBe(true);
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThan(5);
      seen.add(value);
    }
    // With 500 draws over five buckets, every bucket should appear.
    expect(seen.size).toBe(5);
  });
});
