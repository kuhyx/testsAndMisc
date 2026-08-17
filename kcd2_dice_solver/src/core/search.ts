/**
 * Search for the best six-dice loadout that an inventory can field.
 *
 * A set's value is not the sum of its dice's individual values — Farkle scores
 * combinations *across* the six dice (triples, straights, the doubling rule), so
 * ranking dice one at a time and taking the top six is simply wrong. The search
 * therefore evaluates whole sets.
 *
 * Two strategies, picked automatically by problem size: exhaustive enumeration
 * while the space is small enough to prove an answer, and a multi-start hill
 * climb past that. Both live in `searchStrategies.ts`; the pooling of dice that
 * score identically lives in `searchGroups.ts`.
 */

import type { Die } from "../data/dice.ts";
import { evaluateQuick, evaluateSet } from "./evaluate.ts";
import type { Evaluation, QuickEvaluation } from "./evaluate.ts";
import type { Scorer } from "./scoring.ts";
import { SET_SIZE, countCandidates, expand, groupInventory } from "./searchGroups.ts";
import type { InventoryEntry, Selection } from "./searchGroups.ts";
import { Leaderboard, enumerateAll, hillClimb } from "./searchStrategies.ts";
import type { SearchOptions } from "./searchStrategies.ts";

/**
 * Largest number of candidate sets we are willing to enumerate exhaustively.
 * At roughly 4k floating-point operations per candidate this stays well under a
 * second in a worker.
 */
export const EXHAUSTIVE_LIMIT = 300_000;

export interface SearchResult {
  /** The recommended six dice, as concrete dice. */
  readonly dice: readonly Die[];
  /** Exact evaluation of that set. */
  readonly evaluation: Evaluation;
  /** True when the whole space was enumerated, so the result is provably best. */
  readonly optimal: boolean;
  /** Runner-up sets, best first, for context in the UI. */
  readonly alternatives: readonly SetCandidate[];
  /** Ids that were pooled because they score identically to the pick. */
  readonly equivalentIds: readonly string[];
}

export interface SetCandidate {
  readonly dice: readonly Die[];
  readonly evaluation: Evaluation;
}

/**
 * Find the best six-dice loadout an inventory can field.
 *
 * @param inventory - Owned dice with counts.
 * @param scorer - Memoised scorer carrying the active badge rules.
 * @param options - Optional tuning; the defaults are what the UI uses.
 * @returns The recommended set, its evaluation, and runners-up.
 * @throws If the inventory holds fewer than six dice in total.
 */
export function findBestSet(
  inventory: readonly InventoryEntry[],
  scorer: Scorer,
  options: SearchOptions = {},
): SearchResult {
  const groups = groupInventory(inventory);
  const total = groups.reduce((sum, group) => sum + group.available, 0);
  if (total < SET_SIZE) {
    throw new Error(`Need at least ${SET_SIZE} dice, inventory has ${total}`);
  }

  const limit = options.exhaustiveLimit ?? EXHAUSTIVE_LIMIT;
  const board = new Leaderboard((options.alternatives ?? 4) + 1);
  const evaluate = (selection: Selection): QuickEvaluation =>
    evaluateQuick(expand(groups, selection), scorer);

  const optimal = countCandidates(groups) <= limit;
  if (optimal) {
    enumerateAll(groups, (selection) => {
      board.offer(selection, evaluate(selection));
    });
  } else {
    hillClimb(groups, evaluate, board, options);
  }

  // The inventory-size check above guarantees at least one candidate was
  // offered, so `all()` is never empty here.
  const [best, ...rest] = board.all();

  const usedGroups = groups.filter((_, index) => best.selection[index] > 0);
  const bestDice = expand(groups, best.selection);
  return {
    dice: bestDice,
    // Only the handful of sets we actually report pay for the percentile.
    evaluation: evaluateSet(bestDice, scorer),
    optimal,
    alternatives: rest.map((entry) => {
      const dice = expand(groups, entry.selection);
      return { dice, evaluation: evaluateSet(dice, scorer) };
    }),
    equivalentIds: usedGroups.flatMap((group) => group.members),
  };
}
