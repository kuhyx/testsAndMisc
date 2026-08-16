/**
 * The 33 dice badges of Kingdom Come: Deliverance II.
 *
 * Source: https://kingdom-come-deliverance.fandom.com/wiki/Dice/KCD2
 *
 * Badges only take effect when the opponent also brings a badge of the same
 * tier, so the solver recommends one badge per tier rather than a single
 * overall winner.
 *
 * UNVERIFIED CONSTANTS
 * --------------------
 * Neither the fandom wiki nor Inara publishes numeric values for the three
 * "Advantage" formations or for the Headstart point leads — the in-game text is
 * qualitative ("a small point lead"). The constants below are explicit,
 * editable guesses rather than invented data buried in a table; the UI exposes
 * them so they can be corrected from the game's own help screen.
 */

export type BadgeTier = "tin" | "silver" | "gold";

/**
 * Extra scoring formations and multipliers granted by the five badges that
 * change the scoring rules themselves. These are threaded through `bestScore`,
 * so enabling one can change which six dice are optimal.
 */
export interface ScoringRules {
  /** Carpenter's Advantage: the "Cut", a 3 and a 5 together. */
  readonly cut: boolean;
  /** Executioner's Advantage: "The Gallows", a 4, a 5 and a 6. */
  readonly gallows: boolean;
  /** Priest's Advantage: "The Eye", a 1, a 3 and a 5. */
  readonly eye: boolean;
  /** Gold Emperor's badge: triple points for every 1+1+1. */
  readonly emperorTriple: boolean;
  /** Gold Tyche badge: double points for three sixes. */
  readonly tycheDouble: boolean;
}

/** Rule set with every scoring badge switched off. */
export const BASE_RULES: ScoringRules = {
  cut: false,
  gallows: false,
  eye: false,
  emperorTriple: false,
  tycheDouble: false,
};

/**
 * Point values of the three badge-granted formations.
 *
 * UNVERIFIED. Defaulted to what the constituent dice are worth under the
 * ordinary rules, i.e. the formation lets you *use* dice that would otherwise
 * be dead but grants no bonus on top:
 *   Cut    3+5   -> 50 (the 5) is the only ordinary value, rounded up to 150
 *   Gallows 4+5+6 -> 50 (the 5), rounded up to 250
 *   Eye    1+3+5 -> 150 (the 1 and the 5), rounded up to 300
 */
export interface FormationValues {
  readonly cut: number;
  readonly gallows: number;
  readonly eye: number;
}

/** Default, UNVERIFIED formation point values. Editable in the UI. */
export const DEFAULT_FORMATION_VALUES: FormationValues = {
  cut: 150,
  gallows: 250,
  eye: 300,
};

/** What a badge actually does, as a discriminated union. */
export type BadgeEffect =
  /** Changes the scoring table. Evaluated jointly with the dice set. */
  | { readonly kind: "scoring"; readonly rules: Partial<ScoringRules> }
  /** Roll `dice` extra dice, `uses` times per game. */
  | { readonly kind: "extraDice"; readonly dice: number; readonly uses: number }
  /** Reroll up to `dice` dice of your choosing, `uses` times per game. */
  | { readonly kind: "reroll"; readonly dice: number; readonly uses: number }
  /** Re-throw after a bust, `uses` times per game. */
  | { readonly kind: "antibust"; readonly uses: number }
  /** Double the point value of your last throw, `uses` times per game. */
  | { readonly kind: "doubleThrow"; readonly uses: number }
  /** Multiply the whole turn's score by `factor`, `uses` times per game. */
  | { readonly kind: "multiplier"; readonly factor: number; readonly uses: number }
  /** Start the game `points` ahead. */
  | { readonly kind: "headstart"; readonly points: number }
  /** Change a die of your choosing to `value`, `uses` times per game. */
  | { readonly kind: "setDie"; readonly value: number; readonly uses: number }
  /** Purely reactive: cancels an opponent badge of the same tier. */
  | { readonly kind: "defence" };

export interface Badge {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly tier: BadgeTier;
  readonly effect: BadgeEffect;
}

import { BADGES } from "./badgeTable.ts";
import { HEADSTART_POINTS } from "./headstart.ts";

export { BADGES, HEADSTART_POINTS };


/** Lookup from badge id to badge. */
export const BADGES_BY_ID: ReadonlyMap<string, Badge> = new Map(
  BADGES.map((badge) => [badge.id, badge]),
);

/** Tiers in ascending power order, for grouping in the UI and the results. */
export const TIERS: readonly BadgeTier[] = ["tin", "silver", "gold"];
