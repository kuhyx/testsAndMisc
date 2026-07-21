import { describe, expect, it } from "vitest";
import { fuzzyFilter, fuzzyMatch } from "./fuzzy.ts";
import { mulberry32, randomInt } from "./rng.ts";

describe("fuzzyMatch", () => {
  it("matches a subsequence", () => {
    expect(fuzzyMatch("wei", "Weighted die")).not.toBeNull();
    expect(fuzzyMatch("wgt", "Weighted die")).not.toBeNull();
  });

  it("rejects letters that are not present in order", () => {
    expect(fuzzyMatch("zzz", "Weighted die")).toBeNull();
    expect(fuzzyMatch("eiw", "Weighted die")).toBeNull();
  });

  it("treats an empty query as a match with no highlights", () => {
    expect(fuzzyMatch("", "Weighted die")).toEqual({ score: 0, indices: [] });
  });

  it("ignores case and spaces in the query", () => {
    const match = fuzzyMatch("W E I", "Weighted die");
    expect(match?.indices).toEqual([0, 1, 2]);
  });

  it("reports where it matched, for highlighting", () => {
    // The best alignment, not the leftmost one: "die" underlines the word
    // "die" rather than binding its 'd' to the end of "Weighted".
    expect(fuzzyMatch("die", "Weighted die")?.indices).toEqual([9, 10, 11]);
    expect(fuzzyMatch("die", "Ordinary die")?.indices).toEqual([9, 10, 11]);
  });

  it("prefers a whole-word run over an earlier scattered one", () => {
    // "pain" could scatter across "Painter's" or land on it contiguously.
    expect(fuzzyMatch("paint", "Painter's die B")?.indices).toEqual([0, 1, 2, 3, 4]);
  });

  it("scores consecutive matches above scattered ones", () => {
    const consecutive = fuzzyMatch("wei", "Weighted die");
    const scattered = fuzzyMatch("wei", "Wagoner's engraved ivory");
    expect(consecutive?.score).toBeGreaterThan(scattered?.score ?? Infinity);
  });

  it("rewards matching at a word boundary", () => {
    // The 'd' of "die" starts a word; the 'd' inside "Wisdom" does not.
    const boundary = fuzzyMatch("d", "a die");
    const inside = fuzzyMatch("d", "Wisdom");
    expect(boundary?.score).toBeGreaterThan(inside?.score ?? Infinity);
  });
});

describe("fuzzyFilter", () => {
  const names = [
    "Weighted die",
    "Wisdom tooth die",
    "Ordinary die",
    "Painter's die B",
    "Painter's die R",
  ];

  it("finds the die a short prefix is aiming at", () => {
    const results = fuzzyFilter("wei", names, (name) => name);
    expect(results[0].item).toBe("Weighted die");
  });

  it("narrows to one die as the query gets specific", () => {
    const results = fuzzyFilter("paintb", names, (name) => name);
    expect(results[0].item).toBe("Painter's die B");
  });

  it("drops non-matches", () => {
    expect(fuzzyFilter("zzzz", names, (name) => name)).toHaveLength(0);
  });

  it("keeps the original order for an empty query", () => {
    const results = fuzzyFilter("   ", names, (name) => name);
    expect(results.map((result) => result.item)).toEqual(names);
  });
});

describe("mulberry32", () => {
  it("is deterministic for a seed", () => {
    const a = mulberry32(42);
    const b = mulberry32(42);
    expect([a(), a(), a()]).toEqual([b(), b(), b()]);
  });

  it("differs between seeds", () => {
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

  it("bounds randomInt below the given bound", () => {
    const random = mulberry32(9);
    for (let i = 0; i < 500; i += 1) {
      const value = randomInt(random, 5);
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThan(5);
      expect(Number.isInteger(value)).toBe(true);
    }
  });
});
