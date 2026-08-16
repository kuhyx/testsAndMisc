/**
 * Monte Carlo simulation of a full push-your-luck turn.
 *
 * This is the solver's *secondary* objective. Unlike the exact single-roll EV in
 * `evaluate.ts`, a turn's value depends on how the player plays it, and the
 * policy below is an assumption rather than a fact — so it is stated explicitly
 * and its knobs are exposed rather than buried:
 *
 *   1. Only holds in which every set-aside die scores are legal (game rule).
 *   2. Among those, take the hold maximising `points + dieValueBonus * diceLeft`
 *      — i.e. a die still in your hand is worth something, so do not scoop up a
 *      lone 50-point five just because you can.
 *   3. Roll again while the turn total is below `bankThreshold`; bank once it
 *      reaches it.
 *   4. If every die scored, take the free re-roll of all six ("hot dice"),
 *      regardless of the threshold — it costs nothing to be holding zero dice.
 *
 * Turn-level badges are simulated here too, since their whole value is in how
 * they change this loop.
 */

import { CATEGORIES } from "./scoring.ts";
import type { Scorer } from "./scoring.ts";
import type { Random } from "../lib/rng.ts";

/** The push-your-luck policy the simulator plays. */
export interface TurnPolicy {
  /** Bank as soon as the turn total reaches this many points. */
  readonly bankThreshold: number;
  /** Notional worth of keeping one die in hand, used when choosing a hold. */
  readonly dieValueBonus: number;
}

/** Default policy. 300 is the conventional Farkle banking threshold. */
export const DEFAULT_POLICY: TurnPolicy = {
  bankThreshold: 300,
  dieValueBonus: 60,
};

/** Badge charges available to the simulated player, all optional. */
export interface BadgeCharges {
  /** Throws on which one extra die joins the roll. */
  readonly extraDice: number;
  /** Re-throws of the whole hand after a bust. */
  readonly antibust: number;
  /** Throws on which one die is forced to `setDieValue`. */
  readonly setDie: number;
  /** Face a forced die takes, 1-6. */
  readonly setDieValue: number;
  /** Re-rolls of the worst `rerollDice` dice, used to rescue a bust. */
  readonly reroll: number;
  /** How many dice a single re-roll charge may replace. */
  readonly rerollDice: number;
}

/** No badge equipped. */
export const NO_CHARGES: BadgeCharges = {
  extraDice: 0,
  antibust: 0,
  setDie: 0,
  setDieValue: 1,
  reroll: 0,
  rerollDice: 0,
};

/**
 * Sample one category (a face index, or one of the substitute slots) from a die.
 *
 * @param weights - Category weights summing to 1.
 * @param random - Seeded random source.
 * @returns The index of the sampled category.
 */
export function sampleCategory(weights: readonly number[], random: Random): number {
  let target = random();
  let slot = 0;
  // Stop one short: the final category absorbs any floating-point drift that
  // would otherwise let `target` survive the whole sweep.
  for (; slot < CATEGORIES - 1; slot += 1) {
    target -= weights[slot];
    if (target <= 0) {
      return slot;
    }
  }
  return CATEGORIES - 1;
}

/**
 * Roll a hand of dice into a count vector.
 *
 * @param hand - Pre-computed category weights, one entry per die.
 * @param random - Seeded random source.
 * @returns The resulting count vector.
 */
export function roll(hand: readonly (readonly number[])[], random: Random): number[] {
  const counts = new Array<number>(CATEGORIES).fill(0);
  for (const weights of hand) {
    counts[sampleCategory(weights, random)] += 1;
  }
  return counts;
}

/**
 * Every sub-multiset of a roll, as candidate holds.
 *
 * @param counts - Count vector of the roll.
 * @returns All sub-multisets, including the empty one.
 */
export function subMultisets(counts: readonly number[]): number[][] {
  let results: number[][] = [[]];
  for (const available of counts) {
    const next: number[][] = [];
    for (const prefix of results) {
      for (let take = 0; take <= available; take += 1) {
        next.push([...prefix, take]);
      }
    }
    results = next;
  }
  return results;
}

/** The hold the policy chose, plus what it is worth. */
interface Hold {
  readonly points: number;
  readonly used: number;
}

/**
 * Choose which dice to set aside, per rules 1 and 2 of the policy.
 *
 * @param counts - Count vector of the roll.
 * @param scorer - Memoised scorer carrying the active badge rules.
 * @param policy - The push-your-luck policy in force.
 * @returns The chosen hold, or `null` when nothing scores (a bust).
 */
export function chooseHold(
  counts: readonly number[],
  scorer: Scorer,
  policy: TurnPolicy,
): Hold | null {
  const total = counts.reduce((sum, value) => sum + value, 0);
  let best: Hold | null = null;
  let bestUtility = -Infinity;

  for (const candidate of subMultisets(counts)) {
    const used = candidate.reduce((sum, value) => sum + value, 0);
    if (used === 0) {
      continue;
    }
    const points = scorer.scoreUsingAll(candidate);
    if (points === -Infinity) {
      continue;
    }
    const utility = points + policy.dieValueBonus * (total - used);
    if (utility > bestUtility) {
      bestUtility = utility;
      best = { points, used };
    }
  }
  return best;
}

/**
 * Force one die in a roll to a chosen face, spending a Transmutation charge.
 *
 * Every candidate conversion is tried and the best one kept, and the charge is
 * only spent if it actually raises the roll's score. A player would never burn a
 * Tin Transmutation to turn a 1 into a 3, so the model must not either — an
 * earlier version always converted the "least useful" die and consequently
 * valued the tin badge at *minus* 95 points.
 *
 * @param counts - Count vector of the roll, mutated in place when it helps.
 * @param value - The face the die becomes, 1-6.
 * @param scorer - Memoised scorer carrying the active badge rules.
 * @returns True if the charge was spent.
 */
export function applySetDie(counts: number[], value: number, scorer: Scorer): boolean {
  const before = scorer.score(counts);
  let bestFace = -1;
  let bestScore = before;

  for (let face = 1; face <= 6; face += 1) {
    if (face === value || counts[face - 1] === 0) {
      continue;
    }
    counts[face - 1] -= 1;
    counts[value - 1] += 1;
    const after = scorer.score(counts);
    counts[face - 1] += 1;
    counts[value - 1] -= 1;
    if (after > bestScore) {
      bestScore = after;
      bestFace = face;
    }
  }

  if (bestFace === -1) {
    return false;
  }
  counts[bestFace - 1] -= 1;
  counts[value - 1] += 1;
  return true;
}

export {
  simulateTurn,
  simulateTurns,
} from "./simulateTurns.ts";
export type {
  SimulationResult,
} from "./simulateTurns.ts";
