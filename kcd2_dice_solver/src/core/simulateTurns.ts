/**
 * Whole-turn and multi-turn simulation.
 *
 * Split out of simulate.ts to keep it under the 250-line cap.
 */

import type { Die } from "../data/dice.ts";
import {
  applySetDie,
  chooseHold,
  DEFAULT_POLICY,
  NO_CHARGES,
  roll,
  sampleCategory,
} from "./simulate.ts";
import type { BadgeCharges, TurnPolicy } from "./simulate.ts";
import { categoryWeights } from "./distribution.ts";
import type { Scorer } from "./scoring.ts";
import { mulberry32 } from "../lib/rng.ts";
import type { Random } from "../lib/rng.ts";

/**
 * Play one turn and return the points banked.
 *
 * @param dice - The six dice being played.
 * @param scorer - Memoised scorer carrying the active badge rules.
 * @param policy - The push-your-luck policy.
 * @param charges - Badge charges available for this turn.
 * @param random - Seeded random source.
 * @param counter - Optional tally of how many throws the turn took.
 * @returns Points banked; 0 if the turn ended in a bust.
 */
export function simulateTurn(
  dice: readonly Die[],
  scorer: Scorer,
  policy: TurnPolicy,
  charges: BadgeCharges,
  random: Random,
  counter: { throws: number } = { throws: 0 },
): number {
  const allWeights = dice.map(categoryWeights);
  // The extra die a Might badge grants is modelled as another copy of the first
  // die in the loadout — the loadout is uniform in practice, and the game does
  // not say which die it adds.
  const [spare] = allWeights;

  let inHand = allWeights.length;
  let turnTotal = 0;
  let extraDice = charges.extraDice;
  let antibust = charges.antibust;
  let setDie = charges.setDie;
  let reroll = charges.reroll;

  for (;;) {
    const hand = allWeights.slice(0, inHand);
    if (extraDice > 0) {
      hand.push(spare);
      extraDice -= 1;
    }
    let counts = roll(hand, random);
    counter.throws += 1;

    if (setDie > 0 && applySetDie(counts, charges.setDieValue, scorer)) {
      setDie -= 1;
    }

    let hold = chooseHold(counts, scorer, policy);

    if (hold === null && reroll > 0) {
      // Re-roll the least useful dice rather than accept the bust.
      reroll -= 1;
      const replaced = Math.min(charges.rerollDice, hand.length);
      counts = rerollWorst(counts, replaced, hand, random);
      hold = chooseHold(counts, scorer, policy);
    }
    if (hold === null && antibust > 0) {
      antibust -= 1;
      continue;
    }
    if (hold === null) {
      return 0;
    }

    turnTotal += hold.points;
    const remaining = hand.length - hold.used;

    // Banking is checked before the hot-dice re-roll, not after. Hot dice are
    // often described as "free", but they are not: throwing six fresh dice can
    // bust and forfeit the entire turn total. Re-rolling unconditionally also
    // made the loop non-terminating for a die that always scores.
    if (turnTotal >= policy.bankThreshold) {
      return turnTotal;
    }
    // Every continue adds at least 50 points, so the turn always terminates.
    inHand = remaining === 0 ? allWeights.length : remaining;
  }
}

/**
 * Re-roll the least useful dice of a busted roll.
 *
 * @param counts - Count vector of the busted roll.
 * @param howMany - How many dice to replace.
 * @param hand - Category weights of the dice in hand.
 * @param random - Seeded random source.
 * @returns A new count vector with those dice re-rolled.
 */
function rerollWorst(
  counts: readonly number[],
  howMany: number,
  hand: readonly (readonly number[])[],
  random: Random,
): number[] {
  const next = counts.slice();
  const preference = [2, 3, 4, 6, 5, 1];
  let removed = 0;
  for (const face of preference) {
    while (removed < howMany && next[face - 1] > 0) {
      next[face - 1] -= 1;
      removed += 1;
    }
  }
  for (let i = 0; i < removed; i += 1) {
    next[sampleCategory(hand[i], random)] += 1;
  }
  return next;
}

/** Result of a Monte Carlo run. */
export interface SimulationResult {
  /** Mean points banked per turn. */
  readonly meanPerTurn: number;
  /** Standard error of that mean, so noise is visible rather than implied. */
  readonly standardError: number;
  /** Fraction of turns that ended in a bust. */
  readonly bustRate: number;
  /** Mean number of throws made per turn. */
  readonly throwsPerTurn: number;
  /** How many turns were played. */
  readonly turns: number;
}

/**
 * Golden-ratio increment used to derive a distinct stream per turn.
 *
 * Each turn is simulated from its own seed rather than from one long shared
 * stream. That makes badge comparisons *paired*: a turn in which the badge never
 * triggers plays out bit-for-bit identically with and without it, so the
 * measured difference is the badge's effect and not a diverged random stream.
 * With a shared stream the noise swamped the signal — badges that can only ever
 * help were coming out slightly negative.
 */
const TURN_SEED_STEP = 0x9e3779b9;

/**
 * Estimate a dice set's mean banked points per turn.
 *
 * @param dice - The six dice being played.
 * @param scorer - Memoised scorer carrying the active badge rules.
 * @param turns - How many turns to simulate.
 * @param policy - The push-your-luck policy.
 * @param charges - Badge charges available each turn.
 * @param seed - Seed for the random source, so runs are reproducible.
 * @returns Mean, standard error, and bust rate.
 */
export function simulateTurns(
  dice: readonly Die[],
  scorer: Scorer,
  turns: number,
  policy: TurnPolicy = DEFAULT_POLICY,
  charges: BadgeCharges = NO_CHARGES,
  seed = 0x5eed,
): SimulationResult {
  let sum = 0;
  let sumSquares = 0;
  let busts = 0;
  let throws = 0;
  for (let turn = 0; turn < turns; turn += 1) {
    const random = mulberry32((seed + turn * TURN_SEED_STEP) >>> 0);
    const counter = { throws: 0 };
    const banked = simulateTurn(dice, scorer, policy, charges, random, counter);
    sum += banked;
    sumSquares += banked * banked;
    throws += counter.throws;
    if (banked === 0) {
      busts += 1;
    }
  }
  const mean = sum / turns;
  const variance = Math.max(0, sumSquares / turns - mean * mean);
  return {
    meanPerTurn: mean,
    standardError: Math.sqrt(variance / turns),
    bustRate: busts / turns,
    throwsPerTurn: throws / turns,
    turns,
  };
}
