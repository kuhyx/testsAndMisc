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
 * are meant to rank badges against each other, not to predict a scoreline. The
 * baseline they are all measured against lives in `badgeBaseline.ts`.
 */

import type { Badge, ScoringRules } from "../data/badges.ts";
import { BADGES, BASE_RULES, TIERS } from "../data/badges.ts";
import {
  TURNS_PER_GAME,
  bestThrowsValue,
  measureBaseline,
  rankValue,
  singleCharge,
  turnValue,
} from "./badgeBaseline.ts";
import type {
  BadgeBaseline,
  BadgeContext,
  BadgeRecommendation,
  BadgeValuation,
} from "./badgeBaseline.ts";
import { Scorer } from "./scoring.ts";
import { findBestSet } from "./search.ts";

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
 * Round a point figure for display inside a reason string.
 *
 * @param value - The number to format.
 * @returns The value rounded to one decimal place.
 */
function format(value: number): string {
  return value.toFixed(1);
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
