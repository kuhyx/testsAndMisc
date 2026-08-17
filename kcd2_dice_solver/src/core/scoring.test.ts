/**
 * Every row of the wiki's scoring table, asserted directly.
 *
 * https://kingdom-come-deliverance.fandom.com/wiki/Dice/KCD2
 */

import { describe, expect, it } from "vitest";
import { BASE_RULES, DEFAULT_FORMATION_VALUES } from "../data/badges.ts";
import type { ScoringRules } from "../data/badges.ts";
import { CATEGORIES, Scorer, WILD_ALONE, WILD_COMBO } from "./scoring.ts";
import type { WildCounts } from "./scoring.ts";
import { ofAKindValue, tripleBase } from "./scoringMoves.ts";

const plain = (): Scorer => new Scorer(BASE_RULES);
const withRules = (rules: Partial<ScoringRules>): Scorer =>
  new Scorer({ ...BASE_RULES, ...rules }, DEFAULT_FORMATION_VALUES);

/**
 * Build a count vector, for the calls that take one rather than a face list.
 *
 * @param faces - Natural face values in the hand.
 * @param wilds - Substitutes of each kind in the hand.
 * @returns The count vector those dice make.
 */
const countsOf = (faces: readonly number[], wilds: WildCounts = {}): number[] => {
  const counts = new Array<number>(CATEGORIES).fill(0);
  for (const face of faces) {
    counts[face - 1] += 1;
  }
  counts[WILD_ALONE] = wilds.alone ?? 0;
  counts[WILD_COMBO] = wilds.combo ?? 0;
  return counts;
};

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

describe("substitutes", () => {
  // Both joker faces substitute inside combinations, so these cases must come
  // out the same whichever kind of substitute supplies the missing face.
  for (const [kind, wilds] of [
    ["Balatro joker", { alone: 1 }],
    ["devil's head", { combo: 1 }],
  ] as const) {
    it(`lets a ${kind} complete a straight`, () => {
      // 2,3,4,5,6 plus one substitute becomes the full 1-6 straight.
      expect(plain().scoreFaces([2, 3, 4, 5, 6], wilds)).toBe(1500);
    });

    it(`lets a ${kind} complete a triple`, () => {
      // 6,6 + substitute-as-6 is 600, but 2,3,4,6 + substitute-as-5 is the 2-6
      // straight at 750 — the scorer must take the better of the two.
      expect(plain().scoreFaces([6, 6, 2, 3, 4], wilds)).toBe(750);
      // Without the 2-6 straight available, the triple is the best use.
      expect(plain().scoreFaces([6, 6, 2, 2, 4], wilds)).toBe(600);
    });

    it(`extends an n-of-a-kind with a ${kind}`, () => {
      // Three ones and a substitute are a quadruple, per the wiki's example.
      expect(plain().scoreFaces([1, 1, 1, 2, 4], wilds)).toBe(2000);
    });

    it(`never makes a roll worse with a ${kind}`, () => {
      expect(plain().scoreFaces([2, 2, 3, 3, 4], wilds)).toBeGreaterThan(0);
    });
  }

  it("scores a lone Balatro joker as a one", () => {
    // "Picking it alone will count as if you threw 1."
    expect(plain().scoreFaces([], { alone: 1 })).toBe(100);
    expect(plain().scoreFaces([2, 3], { alone: 1 })).toBe(100);
  });

  it("gives a lone devil's head nothing", () => {
    // "Matching any combination but never scoring on its own."
    expect(plain().scoreFaces([], { combo: 1 })).toBe(0);
    expect(plain().scoreFaces([2, 3], { combo: 1 })).toBe(0);
    // Nor may it ride along with a scoring die: a hold must be all scoring dice,
    // and there is no combination for the devil's head to join here.
    expect(plain().scoreUsingAll(countsOf([1], { combo: 1 }))).toBe(-Infinity);
    expect(plain().scoreUsingAll(countsOf([], { alone: 1 }))).toBe(100);
  });

  it("resolves six substitutes to the best possible roll", () => {
    // Six of either kind can form two triples of ones, since a combination may
    // be made entirely of substitutes.
    expect(plain().scoreFaces([], { alone: 6 })).toBe(8000);
    expect(plain().scoreFaces([], { combo: 6 })).toBe(8000);
  });

  it("spends both kinds of substitute on one combination", () => {
    // 2,2 + joker-as-2 + devil-as-2 is a four-of-a-kind, so both slots have to
    // be reachable from the same combination.
    expect(plain().scoreFaces([2, 2], { alone: 1, combo: 1 })).toBe(400);
    expect(plain().scoreFaces([1, 1], { alone: 1, combo: 1 })).toBe(2000);
  });

  it("gives the joker every use the devil's head has, and one more", () => {
    const scorer = plain();
    for (const faces of [[2, 3], [2, 2], [6, 6, 2, 3, 4], [1, 1, 1, 2, 4], [2, 3, 4, 5, 6]]) {
      expect(scorer.scoreFaces(faces, { alone: 1 })).toBeGreaterThanOrEqual(
        scorer.scoreFaces(faces, { combo: 1 }),
      );
    }
    // The one extra: scoring with no combination to join.
    expect(scorer.scoreFaces([2, 3], { alone: 1 })).toBe(100);
    expect(scorer.scoreFaces([2, 3], { combo: 1 })).toBe(0);
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
    expect(scorer.scoreUsingAll(countsOf([1]))).toBe(100);
    // A lone 2 cannot score, so no legal hold uses it.
    expect(scorer.scoreUsingAll(countsOf([2]))).toBe(-Infinity);
    // A 1 plus a dead 2 is still illegal as a hold.
    expect(scorer.scoreUsingAll(countsOf([1, 2]))).toBe(-Infinity);
  });

  it("scores an empty hold as zero", () => {
    expect(plain().scoreUsingAll(countsOf([]))).toBe(0);
  });

  it("resolves substitutes in a hold", () => {
    // A Balatro joker is a legal hold on its own; a devil's head is not.
    expect(plain().scoreUsingAll(countsOf([], { alone: 1 }))).toBe(100);
    expect(plain().scoreUsingAll(countsOf([], { combo: 1 }))).toBe(-Infinity);
    // Both may be held as part of a combination they complete.
    expect(plain().scoreUsingAll(countsOf([2, 2], { combo: 1 }))).toBe(200);
    expect(plain().scoreUsingAll(countsOf([2, 2], { alone: 1 }))).toBe(200);
  });

  it("memoises repeated queries", () => {
    const scorer = plain();
    const first = scorer.scoreUsingAll(countsOf([1, 1, 1]));
    expect(scorer.scoreUsingAll(countsOf([1, 1, 1]))).toBe(first);
  });
});
