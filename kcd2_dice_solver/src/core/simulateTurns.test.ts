/** Whole-turn and multi-turn simulation tests. */

/**
 * Tests for the turn simulator.
 *
 * The simulator encodes a *policy*, not a fact, so these tests pin the policy's
 * stated rules rather than asserting that its output is "correct" play.
 */

import { describe, expect, it } from "vitest";
import { BASE_RULES } from "../data/badges.ts";
import { DICE_BY_ID } from "../data/dice.ts";
import type { Die } from "../data/dice.ts";
import { mulberry32 } from "../lib/rng.ts";
import { Scorer } from "./scoring.ts";
import {
  DEFAULT_POLICY,
  NO_CHARGES,
  simulateTurn,
  simulateTurns,
  } from "./simulate.ts";

const die = (id: string): Die => {
  const found = DICE_BY_ID.get(id);
  if (!found) {
    throw new Error(`no such die: ${id}`);
  }
  return found;
};

const scorer = new Scorer(BASE_RULES);
const sixOrdinary = new Array<Die>(6).fill(die("ordinary"));

/**
 * A die that always rolls the given face, for pinning deterministic behaviour.
 *
 * @param face - The face it always shows, 1-6.
 * @returns Six copies of that die.
 */
const alwaysRolls = (face: number): Die[] =>
  new Array<Die>(6).fill({
    id: `always-${face}`,
    name: `always ${face}`,
    description: "",
    weights: [1, 2, 3, 4, 5, 6].map((f) => (f === face ? 1 : 0)) as unknown as Die["weights"],
    wildcardFaces: [],
    wildScoresAlone: false,
  });

const alwaysTwo = alwaysRolls(2);
const alwaysThree = alwaysRolls(3);

describe("simulateTurn", () => {
  it("banks once the threshold is reached", () => {
    const random = mulberry32(1);
    const banked = simulateTurn(sixOrdinary, scorer, DEFAULT_POLICY, NO_CHARGES, random);
    expect(banked).toBeGreaterThanOrEqual(0);
  });

  it("is reproducible for a given seed", () => {
    const first = simulateTurn(sixOrdinary, scorer, DEFAULT_POLICY, NO_CHARGES, mulberry32(7));
    const second = simulateTurn(sixOrdinary, scorer, DEFAULT_POLICY, NO_CHARGES, mulberry32(7));
    expect(first).toBe(second);
  });

  it("counts the throws it made", () => {
    const counter = { throws: 0 };
    simulateTurn(sixOrdinary, scorer, DEFAULT_POLICY, NO_CHARGES, mulberry32(3), counter);
    expect(counter.throws).toBeGreaterThanOrEqual(1);
  });

  it("brings the whole set back when every die scores", () => {
    // Six weighted dice are ones about two thirds of the time, and with no
    // per-die bonus the policy holds every scoring die — so all six get set
    // aside and the hot-dice branch has to refill the hand. A threshold above
    // one throw's typical score keeps the turn going long enough to see it.
    const weighted = new Array<Die>(6).fill(die("weighted"));
    const counter = { throws: 0 };
    simulateTurn(
      weighted,
      scorer,
      { bankThreshold: 20_000, dieValueBonus: 0 },
      NO_CHARGES,
      mulberry32(5),
      counter,
    );
    expect(counter.throws).toBeGreaterThan(1);
  });

  it("always terminates, even for dice that can never bust", () => {
    // Six dice that always roll a 2 always score (six of a kind, 1600). Before
    // banking was checked ahead of the hot-dice re-roll, this looped forever.
    const banked = simulateTurn(
      alwaysTwo,
      scorer,
      DEFAULT_POLICY,
      NO_CHARGES,
      mulberry32(1),
    );
    expect(banked).toBe(1600);
  });
});

describe("badge charges in a turn", () => {
  const misfortune = new Array<Die>(6).fill(die("misfortune"));

  it("an anti-bust charge can only raise the mean", () => {
    const base = simulateTurns(misfortune, scorer, 2000, DEFAULT_POLICY, NO_CHARGES, 11);
    const rescued = simulateTurns(
      misfortune,
      scorer,
      2000,
      DEFAULT_POLICY,
      { ...NO_CHARGES, antibust: 1 },
      11,
    );
    expect(rescued.meanPerTurn).toBeGreaterThanOrEqual(base.meanPerTurn);
    expect(rescued.bustRate).toBeLessThanOrEqual(base.bustRate);
  });

  it("a re-roll charge can only raise the mean", () => {
    const base = simulateTurns(misfortune, scorer, 2000, DEFAULT_POLICY, NO_CHARGES, 13);
    const rerolled = simulateTurns(
      misfortune,
      scorer,
      2000,
      DEFAULT_POLICY,
      { ...NO_CHARGES, reroll: 1, rerollDice: 3 },
      13,
    );
    expect(rerolled.meanPerTurn).toBeGreaterThanOrEqual(base.meanPerTurn);
  });

  it("an extra die can only raise the mean", () => {
    const base = simulateTurns(sixOrdinary, scorer, 2000, DEFAULT_POLICY, NO_CHARGES, 17);
    const bigger = simulateTurns(
      sixOrdinary,
      scorer,
      2000,
      DEFAULT_POLICY,
      { ...NO_CHARGES, extraDice: 1 },
      17,
    );
    expect(bigger.meanPerTurn).toBeGreaterThanOrEqual(base.meanPerTurn);
  });

  it("a transmutation charge can only raise the mean", () => {
    const base = simulateTurns(sixOrdinary, scorer, 2000, DEFAULT_POLICY, NO_CHARGES, 19);
    const transmuted = simulateTurns(
      sixOrdinary,
      scorer,
      2000,
      DEFAULT_POLICY,
      { ...NO_CHARGES, setDie: 1, setDieValue: 1 },
      19,
    );
    expect(transmuted.meanPerTurn).toBeGreaterThanOrEqual(base.meanPerTurn);
  });
});

describe("simulateTurns", () => {
  it("reports a mean, an error bar, a bust rate and a throw count", () => {
    const result = simulateTurns(sixOrdinary, scorer, 1000);
    expect(result.turns).toBe(1000);
    expect(result.meanPerTurn).toBeGreaterThan(0);
    expect(result.standardError).toBeGreaterThan(0);
    expect(result.bustRate).toBeGreaterThan(0);
    expect(result.bustRate).toBeLessThan(1);
    expect(result.throwsPerTurn).toBeGreaterThanOrEqual(1);
  });

  it("is reproducible for a given seed", () => {
    const a = simulateTurns(sixOrdinary, scorer, 500, DEFAULT_POLICY, NO_CHARGES, 42);
    const b = simulateTurns(sixOrdinary, scorer, 500, DEFAULT_POLICY, NO_CHARGES, 42);
    expect(a.meanPerTurn).toBe(b.meanPerTurn);
  });

  it("reports zero variance when every turn is identical", () => {
    const result = simulateTurns(alwaysTwo, scorer, 50);
    expect(result.meanPerTurn).toBe(1600);
    expect(result.standardError).toBe(0);
    expect(result.bustRate).toBe(0);
  });

  it("reports a total bust for dice that can never score", () => {
    // Two each of 2, 3 and 4 every single throw: no 1, no 5, no three of a
    // kind and no straight, so every turn busts.
    const noScore = [
      ...alwaysTwo.slice(0, 2),
      ...alwaysThree.slice(0, 2),
      ...alwaysRolls(4).slice(0, 2),
    ];
    const result = simulateTurns(noScore, scorer, 20);
    expect(result.meanPerTurn).toBe(0);
    expect(result.standardError).toBe(0);
    expect(result.bustRate).toBe(1);
  });
});
