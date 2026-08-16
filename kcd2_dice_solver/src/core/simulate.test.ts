/**
 * Tests for the turn simulator.
 *
 * The simulator encodes a *policy*, not a fact, so these tests pin the policy's
 * stated rules rather than asserting that its output is "correct" play.
 */

import { describe, expect, it } from "vitest";
import { BASE_RULES } from "../data/badges.ts";
import { Scorer } from "./scoring.ts";
import {
  DEFAULT_POLICY,
  applySetDie,
  chooseHold,
  subMultisets,
} from "./simulate.ts";


const scorer = new Scorer(BASE_RULES);

/**
 * A die that always rolls the given face, for pinning deterministic behaviour.
 *
 * @param face - The face it always shows, 1-6.
 * @returns Six copies of that die.
 */


describe("subMultisets", () => {
  it("enumerates every sub-multiset including the empty one", () => {
    // Two categories holding one die each: 2 x 2 = 4 sub-multisets.
    const counts = [1, 1, 0, 0, 0, 0, 0, 0];
    expect(subMultisets(counts)).toHaveLength(4);
  });

  it("scales with the count in each category", () => {
    // Three of one face: 0, 1, 2 or 3 of them.
    expect(subMultisets([3, 0, 0, 0, 0, 0, 0, 0])).toHaveLength(4);
  });
});

describe("chooseHold", () => {
  it("returns null on a bust", () => {
    expect(chooseHold([0, 2, 2, 1, 0, 1, 0, 0], scorer, DEFAULT_POLICY)).toBeNull();
  });

  it("only ever holds dice that score", () => {
    // One 1 and five dead dice: the only legal hold is that single 1.
    const hold = chooseHold([1, 2, 2, 1, 0, 0, 0, 0], scorer, DEFAULT_POLICY);
    expect(hold).toEqual({ points: 100, used: 1 });
  });

  it("declines a low-value die to keep more dice in hand", () => {
    // A 1 (100) and a 5 (50) with four dead dice. Taking both scores 150 but
    // leaves four dice; taking just the 1 scores 100 and leaves five. With the
    // default 60-point-per-die bonus the policy keeps the extra die.
    const hold = chooseHold([1, 2, 2, 0, 1, 0, 0, 0], scorer, DEFAULT_POLICY);
    expect(hold?.used).toBe(1);
    expect(hold?.points).toBe(100);
  });

  it("takes everything when dice in hand are worth nothing", () => {
    const greedy = { bankThreshold: 300, dieValueBonus: 0 };
    const hold = chooseHold([1, 2, 2, 0, 1, 0, 0, 0], scorer, greedy);
    expect(hold?.used).toBe(2);
    expect(hold?.points).toBe(150);
  });

  it("holds a lone Balatro joker but never a lone devil's head", () => {
    // This is where the two joker faces come apart. A 2, a 3 and a 4 offer no
    // combination for a substitute to join — no pair to extend, too few dice for
    // a straight — so the joker's only use is as a lone 1, which the devil's head
    // may not do. It is also why Balatro's die banks more points per turn than the
    // Devil's head despite the two being worth the same on a single throw.
    const joker = chooseHold([0, 1, 1, 1, 0, 0, 1, 0], scorer, DEFAULT_POLICY);
    expect(joker).toEqual({ points: 100, used: 1 });
    expect(chooseHold([0, 1, 1, 1, 0, 0, 0, 1], scorer, DEFAULT_POLICY)).toBeNull();
  });
});

describe("applySetDie", () => {
  it("converts the die that gains the most", () => {
    // Two 1s and a dead 2: turning the 2 into a 1 completes the 1000 triple.
    const counts = [2, 1, 0, 1, 0, 1, 0, 0];
    expect(applySetDie(counts, 1, scorer)).toBe(true);
    expect(counts[0]).toBe(3);
  });

  it("declines to spend the charge when nothing improves", () => {
    // Six 1s are already worth 8000; converting any of them to a 3 is a loss.
    const counts = [6, 0, 0, 0, 0, 0, 0, 0];
    expect(applySetDie(counts, 3, scorer)).toBe(false);
    expect(counts[0]).toBe(6);
  });

  it("declines when there is no other die to convert", () => {
    const counts = [0, 0, 3, 0, 0, 0, 0, 0];
    expect(applySetDie(counts, 3, scorer)).toBe(false);
  });
});
