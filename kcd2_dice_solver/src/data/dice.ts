/**
 * The 43 dice of Kingdom Come: Deliverance II, with their face distributions.
 *
 * Source (canonical): https://kingdom-come-deliverance.fandom.com/wiki/Dice/KCD2
 * Cross-check:        https://inara.cz/kingdom-come-2/items-dice/
 *
 * The wiki publishes percentages rounded to one decimal place, so most rows do
 * not sum to exactly 100. `normaliseDie` divides through by the row total, which
 * both fixes the rounding and lets us store the raw wiki numbers verbatim — the
 * literals below can be diffed against the wiki without arithmetic.
 *
 * Where Inara disagrees with the wiki the Inara figures are recorded in a
 * comment rather than silently reconciled; the wiki is authoritative here.
 */

/** A die face, 1-6. */
export type Face = 1 | 2 | 3 | 4 | 5 | 6;

/** Raw six-element weight vector, indexed by `face - 1`. */
export type Weights = readonly [number, number, number, number, number, number];

export interface Die {
  /** Stable identifier used in saved inventories and worker messages. */
  readonly id: string;
  /** Display name exactly as the wiki spells it. */
  readonly name: string;
  /** Flavour text from the wiki, shown as a tooltip. */
  readonly description: string;
  /**
   * Probability of each face, already normalised to sum to 1.
   * For faces listed as wildcards this is still the probability of *landing* on
   * that face; the scoring engine then treats the result as a substitute.
   */
  readonly weights: Weights;
  /**
   * Faces that act as a wildcard ("substitute") and may count as any value.
   * Empty for all but two dice.
   */
  readonly wildcardFaces: readonly Face[];
  /**
   * Whether this die's joker also scores when held on its own.
   *
   * True for Balatro's die ("picking it alone will count as if you threw 1"),
   * false for the Devil's head ("never scoring on its own"). Meaningless, and so
   * false, when `wildcardFaces` is empty.
   */
  readonly wildScoresAlone: boolean;
}

/**
 * Divide a raw weight vector by its total so the probabilities sum to exactly 1.
 *
 * @param raw - Wiki percentages (or any non-negative weights) for faces 1-6.
 * @returns The same vector scaled to sum to 1.
 */
export function normalise(raw: Weights): Weights {
  const total = raw[0] + raw[1] + raw[2] + raw[3] + raw[4] + raw[5];
  return [
    raw[0] / total,
    raw[1] / total,
    raw[2] / total,
    raw[3] / total,
    raw[4] / total,
    raw[5] / total,
  ];
}


import { RAW_DICE } from "./rawDice.ts";

/** All dice, sorted by display name, with weights normalised to sum to 1. */
export const DICE: readonly Die[] = RAW_DICE.map((raw) => ({
  id: raw.id,
  name: raw.name,
  description: raw.description,
  weights: normalise(raw.weights),
  wildcardFaces: raw.wildcardFaces ?? [],
  wildScoresAlone: raw.wildScoresAlone ?? false,
})).sort((a, b) => a.name.localeCompare(b.name));

/** Lookup from die id to die, for resolving saved inventories. */
export const DICE_BY_ID: ReadonlyMap<string, Die> = new Map(
  DICE.map((die) => [die.id, die]),
);

/**
 * Most of any single die the game lets you carry into one match.
 *
 * Lives here rather than in the row component because it is a rule about the
 * dice, and both the inventory validator and the UI need it — the validator
 * must not import a component to get at it.
 */
export const MAX_PER_DIE = 6;
