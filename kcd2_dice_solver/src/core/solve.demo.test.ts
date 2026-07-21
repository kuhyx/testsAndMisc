/**
 * Sanity oracles for the solver.
 *
 * These are the "would a human immediately call this wrong?" checks: a die that
 * is obviously the best choice must be chosen, a die that is obviously worse
 * than a plain one must be refused, and the counter-intuitive case (a die loaded
 * onto a worthless face still beating a fair die, because six of a kind pays
 * 1600) must come out right — that last one is what proves the search scores
 * whole sets rather than ranking dice individually.
 */

import { describe, expect, it } from "vitest";
import { solve } from "./solve.ts";

/** Six of the same die id, for comparing against a solve result. */
const sixOf = (id: string): string[] => new Array<string>(6).fill(id);

describe("solver sanity oracles", () => {
  it("takes six Weighted dice when they are available", () => {
    // Weighted die rolls a 1 (100 points, and the 1000-point triple) 66.7% of
    // the time. Nothing in the game beats six of them.
    const result = solve({
      diceCounts: { weighted: 6, ordinary: 20 },
      badgeIds: [],
      simulationTurns: 2000,
    });
    expect(result.dice.map((die) => die.id)).toEqual(sixOf("weighted"));
    expect(result.evaluation.ev).toBeGreaterThan(2000);
    expect(result.evaluation.bustProbability).toBeLessThan(0.01);
  });

  it("rejects the Die of misfortune in favour of plain ordinary dice", () => {
    // Spread across 2/3/4/5 with only 4.5% ones and 4.5% sixes, it scores worse
    // than an ordinary die, so a correct solver must refuse it.
    const result = solve({
      diceCounts: { misfortune: 6, ordinary: 20 },
      badgeIds: [],
      simulationTurns: 2000,
    });
    expect(result.dice.map((die) => die.id)).toEqual(sixOf("ordinary"));
  });

  it("prefers a die concentrated on any one face over a fair die", () => {
    // Grozav's die is 66.7% twos. A two is worth nothing on its own, but six of
    // a kind is 1600 points, so concentration beats fairness.
    const result = solve({
      diceCounts: { grozav: 6, ordinary: 20 },
      badgeIds: [],
      simulationTurns: 2000,
    });
    expect(result.dice.map((die) => die.id)).toEqual(sixOf("grozav"));
  });

  it("reports a provably optimal answer for a small inventory", () => {
    const result = solve({
      diceCounts: { weighted: 3, ordinary: 3, lucky: 2 },
      badgeIds: [],
      simulationTurns: 500,
    });
    expect(result.optimal).toBe(true);
    expect(result.dice).toHaveLength(6);
  });

  it("refuses to solve an inventory of fewer than six dice", () => {
    expect(() => solve({ diceCounts: { ordinary: 5 }, badgeIds: [] })).toThrow(
      /at least 6 dice/,
    );
  });
});
