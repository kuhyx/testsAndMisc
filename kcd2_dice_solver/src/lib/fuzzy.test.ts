import { describe, expect, it } from "vitest";
import { DICE } from "../data/dice.ts";
import { fuzzyFilter, fuzzyMatch } from "./fuzzy.ts";

describe("fuzzyMatch", () => {
  it("matches an empty query against anything, scoring zero", () => {
    expect(fuzzyMatch("", "Weighted die")).toEqual({ score: 0, indices: [] });
  });

  it("returns null when a character is missing", () => {
    expect(fuzzyMatch("zzz", "Weighted die")).toBeNull();
  });

  it("matches a subsequence and reports where", () => {
    const match = fuzzyMatch("wei", "Weighted die");
    expect(match?.indices).toEqual([0, 1, 2]);
  });

  it("ignores spaces in the query", () => {
    expect(fuzzyMatch("pain b", "Painter's die B")).not.toBeNull();
  });

  it("rewards consecutive characters over scattered ones", () => {
    const consecutive = fuzzyMatch("luck", "Lucky die");
    const scattered = fuzzyMatch("luck", "Lousy gambler's cheek");
    expect(consecutive?.score).toBeGreaterThan(scattered?.score ?? Infinity);
  });

  it("rewards matches at a word boundary", () => {
    // The 'd' of "die" is at a boundary in both, but "Odd die" is shorter and
    // starts its match at index 0.
    const boundary = fuzzyMatch("od", "Odd die");
    expect(boundary).not.toBeNull();
  });
});

describe("fuzzyFilter", () => {
  const byName = (die: { name: string }): string => die.name;

  it("keeps the original order for an empty query", () => {
    const result = fuzzyFilter("", DICE, byName);
    expect(result.map((match) => match.item.id)).toEqual(DICE.map((die) => die.id));
  });

  it("finds the Weighted die from a three-letter prefix", () => {
    const result = fuzzyFilter("wei", DICE, byName);
    expect(result[0]?.item.id).toBe("weighted");
  });

  it("finds Painter's die B specifically", () => {
    const result = fuzzyFilter("painb", DICE, byName);
    expect(result[0]?.item.id).toBe("painters_b");
  });

  it("returns nothing when no name matches", () => {
    expect(fuzzyFilter("qqqq", DICE, byName)).toEqual([]);
  });
});
