/**
 * Estimating what a badge is worth, in points gained over a whole game.
 *
 * Badges fall into two families and are valued differently, because pretending
 * one model fits both would be wrong in a way the number would hide:
 *
 *   Scoring badges (Carpenter, Executioner, Priest, Emperor, Tyche) change the
 *   scoring table. They are valued by re-running the *entire dice search* with
 *   their rule active and comparing the resulting turn value — so equipping one
 *   can change which six dice you should bring.
 *
 *   Turn-level badges (Might, Fortune, Wedding, Resurrection, Swap-out,
 *   Transmutation, Doppelganger, Warlord, Headstart, Bird King) do not change
 *   what a roll is worth, only what you can do about it. Each charge is
 *   simulated once and the per-charge uplift multiplied by the number of uses.
 *
 *   Defence badges are purely reactive — their worth is exactly whatever the
 *   opponent's badge would have done, which is unknowable at pick time. They
 *   are reported as situational rather than given a fabricated number.
 *
 * Every number here is an estimate built on the simulator's stated policy. They
 * are meant to rank badges against each other, not to predict a scoreline.
 */

import type { Badge, BadgeTier, FormationValues, ScoringRules } from "../data/badges.ts";
import { BADGES, BASE_RULES, DEFAULT_FORMATION_VALUES, TIERS } from "../data/badges.ts";
import type { Die } from "../data/dice.ts";
import { evaluateSet, scoreDistribution } from "./evaluate.ts";
import type { ScoreDistribution } from "./evaluate.ts";
import { Scorer } from "./scoring.ts";
import { findBestSet } from "./search.ts";
import type { InventoryEntry, SearchOptions } from "./search.ts";
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
function turnValue(
  dice: readonly Die[],
  scorer: Scorer,
  policy: TurnPolicy,
  charges: BadgeCharges,
  seed: number,
): number {
  return simulateTurns(dice, scorer, BADGE_SIMULATION_TURNS, policy, charges, seed).meanPerTurn;
}

/**
 * The baseline every badge is measured against: the no-badge loadout's scorer,
 * its simulated turn value, and its exact throw evaluation.
 *
 * Computed once per solve rather than once per badge — recomputing a 4,000-turn
 * simulation thirty-three times was the single largest cost in the first
 * version of this module.
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
 * Value one badge in points gained per game.
 *
 * @param badge - The badge to value.
 * @param context - Inventory, baseline loadout, and simulation settings.
 * @param baseline - The no-badge baseline to compare against.
 * @returns The valuation, including any change to the recommended dice.
 */
export function valueBadge(
  badge: Badge,
  context: BadgeContext,
  baseline: BadgeBaseline = measureBaseline(context),
): BadgeValuation {
  const { baselineDice, formationValues, policy, seed } = context;
  const { scorer: baseScorer, turn: baseTurn } = baseline;
  const effect = badge.effect;

  switch (effect.kind) {
    case "scoring": {
      const rules: ScoringRules = { ...BASE_RULES, ...effect.rules };
      const scorer = new Scorer(rules, formationValues);
      // The rule change can make different dice optimal, so re-run the search.
      const search = findBestSet(context.inventory, scorer, context.searchOptions);
      // Valued on the *exact* per-throw EV delta rather than by simulation.
      // Adding a formation can only ever raise a roll's best score, so this
      // difference is provably non-negative — whereas comparing two simulated
      // turn values let noise report a strictly-better rule as a loss.
      const delta = search.evaluation.ev - baseline.ev;
      return {
        badge,
        pointsPerGame: delta * baseline.throwsPerTurn * TURNS_PER_GAME,
        reason: `Changes the scoring table: +${format(delta)} expected points per throw (${format(baseline.throwsPerTurn)} throws/turn, ${TURNS_PER_GAME} turns/game).`,
        dice: search.dice,
      };
    }
    case "headstart": {
      return {
        badge,
        pointsPerGame: effect.points,
        reason: `Flat lead of ${effect.points} points (UNVERIFIED: the game only says "small"/"moderate"/"large").`,
        dice: null,
      };
    }
    case "multiplier": {
      // Saved for a good turn, so valued against a 90th-percentile throw run
      // rather than an average one.
      const good = baseline.p90 + baseTurn;
      const gain = (effect.factor - 1) * good * effect.uses;
      return {
        badge,
        pointsPerGame: gain,
        reason: `x${effect.factor} on ${effect.uses} good turn(s), valued against a 90th-percentile turn.`,
        dice: null,
      };
    }
    case "doubleThrow": {
      const throwsPerGame = baseline.throwsPerTurn * TURNS_PER_GAME;
      const gain = bestThrowsValue(baseline.distribution, effect.uses, throwsPerGame);
      return {
        badge,
        pointsPerGame: gain,
        reason: `Repeats your ${effect.uses} best throw(s) out of roughly ${Math.round(throwsPerGame)} in a game.`,
        dice: null,
      };
    }
    case "extraDice":
    case "antibust":
    case "reroll":
    case "setDie": {
      const charges = singleCharge(badge);
      const perCharge =
        turnValue(baselineDice, baseScorer, policy, charges, seed) - baseTurn;
      const { uses } = effect;
      return {
        badge,
        pointsPerGame: perCharge * uses,
        reason: `Simulated uplift of ${format(perCharge)} points per charge, ${uses} charge(s) per game.`,
        dice: null,
      };
    }
    case "defence": {
      return {
        badge,
        pointsPerGame: null,
        reason: "Situational: worth exactly whatever the opponent's badge would have done.",
        dice: null,
      };
    }
  }
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
 * Round a point figure for display inside a reason string.
 *
 * @param value - The number to format.
 * @returns The value rounded to one decimal place.
 */
function format(value: number): string {
  return value.toFixed(1);
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

/**
 * Rank the badges the player owns, one list per tier.
 *
 * @param ownedBadgeIds - Ids of badges in the player's inventory.
 * @param context - Inventory, baseline loadout, and simulation settings.
 * @returns One recommendation per tier that has at least one owned badge.
 */
export function recommendBadges(
  ownedBadgeIds: ReadonlySet<string>,
  context: BadgeContext,
): BadgeRecommendation[] {
  const recommendations: BadgeRecommendation[] = [];
  const baseline = measureBaseline(context);
  for (const tier of TIERS) {
    const owned = BADGES.filter(
      (badge) => badge.tier === tier && ownedBadgeIds.has(badge.id),
    );
    if (owned.length === 0) {
      continue;
    }
    const ranked = owned
      .map((badge) => valueBadge(badge, context, baseline))
      .sort((a, b) => rankValue(b) - rankValue(a));
    recommendations.push({ tier, ranked });
  }
  return recommendations;
}

/** Defaults used when the caller does not care. */
export const DEFAULT_BADGE_CONTEXT = {
  formationValues: DEFAULT_FORMATION_VALUES,
  policy: DEFAULT_POLICY,
  seed: 0x5eed,
} as const;
