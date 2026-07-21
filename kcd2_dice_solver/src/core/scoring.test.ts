/**
 * Every row of the wiki's scoring table, asserted directly.
 *
 * https://kingdom-come-deliverance.fandom.com/wiki/Dice/KCD2
 */

import { describe, expect, it } from "vitest";
import { BASE_RULES, DEFAULT_FORMATION_VALUES } from "../data/badges.ts";
import type { ScoringRules } from "../data/badges.ts";
import { Scorer, ofAKindValue, tripleBase } from "./scoring.ts";

const plain = (): Scorer => new Scorer(BASE_RULES);
const withRules = (rules: Partial<ScoringRules>): Scorer =>
  new Scorer({ ...BASE_RULES, ...rules }, DEFAULT_FORMATION_VALUES);

describe("wiki scoring table", () => {
  it("scores a single one and a single five", () => {
    expect(plain().scoreFaces([1, 2, 2, 3, 4, 4])).toBe(100);
    expect(plain().scoreFaces([5, 2, 2, 3, 4, 4])).toBe(50);
    expect(plain().scoreFaces([1, 5, 2, 2, 4, 4])).toBe(150);
  });

  it("scores three of a kind for every face", () => {
    const scorer = plain();
    // Padded with 2s and 4s, which score nothing on their own.
    expect(scorer.scoreFaces([1, 1, 1, 2, 4, 4])).toBe(1000);
    expect(scorer.scoreFaces([2, 2, 2, 4, 4, 3])).toBe(200);
    expect(scorer.scoreFaces([3, 3, 3, 2, 4, 4])).toBe(300);
    expect(scorer.scoreFaces([4, 4, 4, 2, 2, 3])).toBe(400);
    expect(scorer.scoreFaces([5, 5, 5, 2, 4, 4])).toBe(500);
    expect(scorer.scoreFaces([6, 6, 6, 2, 4, 4])).toBe(600);
  });

  it("doubles the value for each die beyond three", () => {
    const scorer = plain();
    // The wiki illustrates this on twos: 200 -> 400 -> 800 -> 1600.
    expect(scorer.scoreFaces([2, 2, 2, 2, 4, 3])).toBe(400);
    expect(scorer.scoreFaces([2, 2, 2, 2, 2, 3])).toBe(800);
    expect(scorer.scoreFaces([2, 2, 2, 2, 2, 2])).toBe(1600);
    // And on ones, where the base is 1000.
    expect(scorer.scoreFaces([1, 1, 1, 1, 4, 3])).toBe(2000);
    expect(scorer.scoreFaces([1, 1, 1, 1, 1, 3])).toBe(4000);
    expect(scorer.scoreFaces([1, 1, 1, 1, 1, 1])).toBe(8000);
  });

  it("scores the three straights", () => {
    const scorer = plain();
    // The sixth die is a dead 3: the straight already consumed the only 1 and
    // the only 5, so there is nothing left to add.
    expect(scorer.scoreFaces([1, 2, 3, 4, 5, 3])).toBe(500);
    expect(scorer.scoreFaces([2, 3, 4, 5, 6, 3])).toBe(750);
    expect(scorer.scoreFaces([1, 2, 3, 4, 5, 6])).toBe(1500);
  });

  it("reports a bust as zero", () => {
    expect(plain().scoreFaces([2, 2, 3, 3, 4, 6])).toBe(0);
  });

  it("picks the best partition rather than the first one found", () => {
    // Six 1s could be scored as two tripled... no: as 3+3 (1000+1000) or as
    // six-of-a-kind (8000). The maximisation must find the latter.
    expect(plain().scoreFaces([1, 1, 1, 1, 1, 1])).toBe(8000);
    // 1,1,1,5,5,5 is two triples, not a triple plus singles.
    expect(plain().scoreFaces([1, 1, 1, 5, 5, 5])).toBe(1500);
  });

  it("exposes the combination formulas", () => {
    expect(tripleBase(1)).toBe(1000);
    expect(tripleBase(4)).toBe(400);
    expect(ofAKindValue(3, 3)).toBe(300);
    expect(ofAKindValue(3, 5)).toBe(1200);
  });
});

describe("wildcards", () => {
  it("lets a wildcard complete a straight", () => {
    // 2,3,4,5,6 plus one wildcard becomes the full 1-6 straight.
    expect(plain().scoreFaces([2, 3, 4, 5, 6], 1)).toBe(1500);
  });

  it("lets a wildcard complete a triple", () => {
    // 6,6 + wildcard-as-6 is 600, but 2,3,4,6 + wildcard-as-5 is the 2-6
    // straight at 750 — the scorer must take the better of the two.
    expect(plain().scoreFaces([6, 6, 2, 3, 4], 1)).toBe(750);
    // Without the 2-6 straight available, the triple is the best use.
    expect(plain().scoreFaces([6, 6, 2, 2, 4], 1)).toBe(600);
  });

  it("resolves six wildcards to the best possible roll", () => {
    // Balatro's die: every face is a wildcard, so six of them are six ones.
    expect(plain().scoreFaces([], 6)).toBe(8000);
  });

  it("never makes a roll worse", () => {
    const scorer = plain();
    expect(scorer.scoreFaces([2, 2, 3, 3, 4], 1)).toBeGreaterThan(0);
  });
});

describe("badge scoring rules", () => {
  it("adds the Carpenter's Cut", () => {
    // 3+5 alone is worth 50 normally (the five); the Cut makes it 150.
    expect(plain().scoreFaces([3, 5, 2, 2, 4, 4])).toBe(50);
    expect(withRules({ cut: true }).scoreFaces([3, 5, 2, 2, 4, 4])).toBe(150);
  });

  it("adds the Executioner's Gallows", () => {
    // Padded so neither a straight (no 3) nor a triple is available.
    expect(plain().scoreFaces([4, 5, 6, 2, 2, 6])).toBe(50);
    expect(withRules({ gallows: true }).scoreFaces([4, 5, 6, 2, 2, 6])).toBe(250);
  });

  it("adds the Priest's Eye", () => {
    // Padded so no straight is available (no 2, no 4).
    expect(plain().scoreFaces([1, 3, 5, 6, 6, 3])).toBe(150);
    expect(withRules({ eye: true }).scoreFaces([1, 3, 5, 6, 6, 3])).toBe(300);
  });

  it("triples the Emperor's 1+1+1 but not its extensions", () => {
    expect(withRules({ emperorTriple: true }).scoreFaces([1, 1, 1, 2, 4, 4])).toBe(3000);
    // Four ones: either the plain four-of-a-kind (2000) or a tripled triple plus
    // a single one (3000 + 100). The better reading wins on its own merits.
    expect(withRules({ emperorTriple: true }).scoreFaces([1, 1, 1, 1, 2, 4])).toBe(3100);
  });

  it("doubles the Tyche three sixes", () => {
    expect(withRules({ tycheDouble: true }).scoreFaces([6, 6, 6, 2, 4, 4])).toBe(1200);
  });

  it("leaves other faces alone under Emperor and Tyche", () => {
    const scorer = withRules({ emperorTriple: true, tycheDouble: true });
    expect(scorer.scoreFaces([3, 3, 3, 2, 4, 4])).toBe(300);
  });
});

describe("scoreUsingAll", () => {
  it("requires every die to be part of a combination", () => {
    const scorer = plain();
    expect(scorer.scoreUsingAll([1, 0, 0, 0, 0, 0, 0])).toBe(100);
    // A lone 2 cannot score, so no legal hold uses it.
    expect(scorer.scoreUsingAll([0, 1, 0, 0, 0, 0, 0])).toBe(-Infinity);
    // A 1 plus a dead 2 is still illegal as a hold.
    expect(scorer.scoreUsingAll([1, 1, 0, 0, 0, 0, 0])).toBe(-Infinity);
  });

  it("scores an empty hold as zero", () => {
    expect(plain().scoreUsingAll([0, 0, 0, 0, 0, 0, 0])).toBe(0);
  });

  it("resolves wildcards in a hold", () => {
    expect(plain().scoreUsingAll([0, 0, 0, 0, 0, 0, 1])).toBe(100);
  });

  it("memoises repeated queries", () => {
    const scorer = plain();
    const first = scorer.scoreUsingAll([3, 0, 0, 0, 0, 0, 0]);
    expect(scorer.scoreUsingAll([3, 0, 0, 0, 0, 0, 0])).toBe(first);
  });
});
