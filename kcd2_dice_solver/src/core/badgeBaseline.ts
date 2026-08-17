/**
 * What a badge is measured *against*: the shared valuation vocabulary and the
 * no-badge baseline every estimate in `badgeValue.ts` is a delta from.
 *
 * The baseline is computed once per solve rather than once per badge —
 * recomputing a 4,000-turn simulation thirty-three times was the single largest
 * cost in the first version of this module.
 */

import type { Badge, BadgeTier, FormationValues } from "../data/badges.ts";
import { BASE_RULES, DEFAULT_FORMATION_VALUES } from "../data/badges.ts";
import type { Die } from "../data/dice.ts";
import { evaluateSet, scoreDistribution } from "./evaluate.ts";
import type { ScoreDistribution } from "./evaluate.ts";
import { Scorer } from "./scoring.ts";
import type { InventoryEntry } from "./searchGroups.ts";
import type { SearchOptions } from "./searchStrategies.ts";
import { DEFAULT_POLICY, NO_CHARGES, simulateTurns } from "./simulate.ts";
import type { BadgeCharges, TurnPolicy } from "./simulate.ts";

/** How many turns a game is assumed to last, for scaling per-turn uplifts. */
export const TURNS_PER_GAME = 8;

/** Turns simulated when valuing a badge. Enough to rank, cheap enough to feel instant. */
export const BADGE_SIMULATION_TURNS = 4000;

export interface BadgeValuation {
  readonly badge: Badge;
  /** Estimated points gained over a game, or null for situational badges. */
  readonly pointsPerGame: number | null;
  /** One-line explanation of where the number came from. */
  readonly reason: string;
  /** The dice this badge implies, when it changes the optimal loadout. */
  readonly dice: readonly Die[] | null;
}

export interface BadgeRecommendation {
  readonly tier: BadgeTier;
  readonly ranked: readonly BadgeValuation[];
}

/** Inputs shared by every badge valuation in one solve. */
export interface BadgeContext {
  readonly inventory: readonly InventoryEntry[];
  readonly baselineDice: readonly Die[];
  readonly formationValues: FormationValues;
  readonly policy: TurnPolicy;
  readonly seed: number;
  readonly searchOptions: SearchOptions;
}

/**
 * The baseline every badge is measured against: the no-badge loadout's scorer,
 * its simulated turn value, and its exact throw evaluation.
 */
export interface BadgeBaseline {
  readonly scorer: Scorer;
  readonly turn: number;
  readonly p90: number;
  /** Exact expected score of one throw of the baseline loadout. */
  readonly ev: number;
  /** Mean throws per turn, used to convert a per-throw delta into a per-game one. */
  readonly throwsPerTurn: number;
  /** Exact single-throw score distribution of the baseline loadout. */
  readonly distribution: ScoreDistribution;
}

/**
 * Mean banked points per turn for a set under a rule set.
 *
 * @param dice - The six dice played.
 * @param scorer - Memoised scorer for the active rules.
 * @param policy - Push-your-luck policy.
 * @param charges - Badge charges available that turn.
 * @param seed - Random seed, held constant across comparisons so that
 *   differences reflect the badge and not simulation noise.
 * @returns Mean points banked per turn.
 */
export function turnValue(
  dice: readonly Die[],
  scorer: Scorer,
  policy: TurnPolicy,
  charges: BadgeCharges,
  seed: number,
): number {
  return simulateTurns(dice, scorer, BADGE_SIMULATION_TURNS, policy, charges, seed).meanPerTurn;
}

/**
 * Total value of the best `uses` throws a player will see in a game.
 *
 * A badge with three charges is not worth three 90th-percentile throws: over the
 * ten-or-so throws in a game you get roughly one 90th-percentile throw, one
 * 80th, one 70th. Valuing each charge at the same optimistic percentile
 * over-rated the three-charge gold badges noticeably.
 *
 * @param distribution - Single-throw score distribution.
 * @param uses - How many charges the badge has.
 * @param throwsPerGame - How many throws the player expects to make.
 * @returns Summed value of the `uses` best throws.
 */
export function bestThrowsValue(
  distribution: ScoreDistribution,
  uses: number,
  throwsPerGame: number,
): number {
  let total = 0;
  for (let k = 1; k <= uses; k += 1) {
    // The k-th best of N throws sits near the (1 - k/N) quantile. Clamped so a
    // short game cannot push the estimate below the median.
    const fraction = Math.min(0.99, Math.max(0.5, 1 - k / Math.max(1, throwsPerGame)));
    total += distribution.at(fraction);
  }
  return total;
}

/**
 * Measure the no-badge baseline for a loadout.
 *
 * @param context - Inventory, baseline loadout, and simulation settings.
 * @returns The scorer, turn value, and 90th-percentile throw score.
 */
export function measureBaseline(context: BadgeContext): BadgeBaseline {
  const scorer = new Scorer(BASE_RULES, context.formationValues);
  const simulation = simulateTurns(
    context.baselineDice,
    scorer,
    BADGE_SIMULATION_TURNS,
    context.policy,
    NO_CHARGES,
    context.seed,
  );
  const evaluation = evaluateSet(context.baselineDice, scorer);
  return {
    scorer,
    turn: simulation.meanPerTurn,
    throwsPerTurn: simulation.throwsPerTurn,
    p90: evaluation.p90,
    ev: evaluation.ev,
    distribution: scoreDistribution(context.baselineDice, scorer),
  };
}

/**
 * Build the charge set that gives a badge exactly one use, for per-charge
 * measurement.
 *
 * @param badge - The badge whose effect to model.
 * @returns Charges with one use of that badge and nothing else.
 */
export function singleCharge(badge: Badge): BadgeCharges {
  const effect = badge.effect;
  switch (effect.kind) {
    case "extraDice":
      return { ...NO_CHARGES, extraDice: 1 };
    case "antibust":
      return { ...NO_CHARGES, antibust: 1 };
    case "reroll":
      return { ...NO_CHARGES, reroll: 1, rerollDice: effect.dice };
    case "setDie":
      return { ...NO_CHARGES, setDie: 1, setDieValue: effect.value };
    default:
      // Scoring, multiplier, doubleThrow, headstart and defence badges are
      // valued analytically rather than simulated, so they carry no charges.
      return NO_CHARGES;
  }
}

/**
 * Sort key for a valuation: situational badges rank below every scored one
 * rather than being dropped from the list.
 *
 * @param valuation - The valuation to rank.
 * @returns Its points per game, or negative infinity when situational.
 */
export function rankValue(valuation: BadgeValuation): number {
  return valuation.pointsPerGame ?? -Infinity;
}

/** Defaults used when the caller does not care. */
export const DEFAULT_BADGE_CONTEXT = {
  formationValues: DEFAULT_FORMATION_VALUES,
  policy: DEFAULT_POLICY,
  seed: 0x5eed,
} as const;
