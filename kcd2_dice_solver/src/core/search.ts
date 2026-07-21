/**
 * Search for the best six-dice loadout that an inventory can field.
 *
 * A set's value is not the sum of its dice's individual values — Farkle scores
 * combinations *across* the six dice (triples, straights, the doubling rule), so
 * ranking dice one at a time and taking the top six is simply wrong. The search
 * therefore evaluates whole sets.
 *
 * Two strategies, picked automatically by problem size:
 *
 *   exhaustive  every size-6 multiset the inventory allows; provably optimal
 *   hillClimb   multi-start local search over single-die swaps; labelled as
 *               heuristic in the result so it is never mistaken for a proof
 *
 * Before either runs, dice whose *scoring* behaviour is identical are merged.
 * Nine of the game's dice are plain uniform 16.7% dice under different names,
 * and the three Painter's dice share one distribution, so this alone removes a
 * large amount of duplicate work.
 */

import type { Die } from "../data/dice.ts";
import { categoryWeights } from "./distribution.ts";
import { evaluateQuick, evaluateSet } from "./evaluate.ts";
import type { Evaluation, QuickEvaluation } from "./evaluate.ts";
import type { Scorer } from "./scoring.ts";
import { mulberry32, randomInt } from "../lib/rng.ts";

/** How many dice go into a loadout. */
export const SET_SIZE = 6;

/**
 * Largest number of candidate sets we are willing to enumerate exhaustively.
 * At roughly 4k floating-point operations per candidate this stays well under a
 * second in a worker.
 */
export const EXHAUSTIVE_LIMIT = 300_000;

/** One line of the user's inventory. */
export interface InventoryEntry {
  readonly die: Die;
  readonly count: number;
}

/** A group of dice that score identically, pooled into one searchable type. */
interface DiceGroup {
  /** Representative die, used for evaluation. */
  readonly die: Die;
  /** Every die id in the group, so the UI can explain the substitution. */
  readonly members: readonly string[];
  /** Total number of interchangeable dice available across the group. */
  readonly available: number;
}

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
 * Merge dice whose category-weight vectors are identical.
 *
 * @param inventory - Owned dice with their counts; zero counts are ignored.
 * @returns One group per distinct scoring behaviour.
 */
export function groupInventory(inventory: readonly InventoryEntry[]): DiceGroup[] {
  const groups = new Map<string, { die: Die; members: string[]; available: number }>();
  for (const entry of inventory) {
    if (entry.count <= 0) {
      continue;
    }
    // Round to 9 decimals so renormalisation noise cannot split a real group.
    const key = categoryWeights(entry.die)
      .map((weight) => weight.toFixed(9))
      .join(",");
    const existing = groups.get(key);
    if (existing) {
      existing.members.push(entry.die.id);
      existing.available += entry.count;
    } else {
      groups.set(key, { die: entry.die, members: [entry.die.id], available: entry.count });
    }
  }
  return [...groups.values()].map((group) => ({
    die: group.die,
    members: group.members,
    // Never search past six of a kind: a loadout is only six dice.
    available: Math.min(group.available, SET_SIZE),
  }));
}

/**
 * Count how many size-6 multisets an inventory admits.
 *
 * Used to decide between exhaustive and heuristic search without ever building
 * the list, so an enormous inventory cannot blow up memory just to be measured.
 *
 * @param groups - Pooled dice groups.
 * @returns The number of distinct loadouts, capped at `Number.MAX_SAFE_INTEGER`.
 */
export function countCandidates(groups: readonly DiceGroup[]): number {
  // ways[k] = number of ways to choose k dice from the groups seen so far.
  let ways = new Array<number>(SET_SIZE + 1).fill(0);
  ways[0] = 1;
  for (const group of groups) {
    const next = new Array<number>(SET_SIZE + 1).fill(0);
    for (let taken = 0; taken <= SET_SIZE; taken += 1) {
      const base = ways[taken];
      for (let take = 0; take <= group.available && taken + take <= SET_SIZE; take += 1) {
        next[taken + take] += base;
      }
    }
    ways = next;
  }
  return ways[SET_SIZE];
}

/** A candidate expressed as how many dice are taken from each group. */
type Selection = number[];

/**
 * Expand a per-group selection into the concrete dice it stands for.
 *
 * @param groups - Pooled dice groups, in the same order as the selection.
 * @param selection - How many dice to take from each group.
 * @returns The six dice of the loadout.
 */
function expand(groups: readonly DiceGroup[], selection: Selection): Die[] {
  const dice: Die[] = [];
  groups.forEach((group, index) => {
    for (let n = 0; n < selection[index]; n += 1) {
      dice.push(group.die);
    }
  });
  return dice;
}

/** Keeps the best few candidates seen, so the UI can show runners-up. */
class Leaderboard {
  private readonly entries: { selection: Selection; evaluation: QuickEvaluation }[] = [];

  /** Signatures already offered, so one loadout cannot occupy several slots. */
  private readonly seen = new Set<string>();

  /**
   * @param capacity - How many candidates to retain, best first.
   */
  constructor(private readonly capacity: number) {}

  /**
   * Offer a candidate to the leaderboard.
   *
   * @param selection - Per-group counts of the candidate.
   * @param evaluation - Its exact evaluation.
   */
  offer(selection: Selection, evaluation: QuickEvaluation): void {
    // The hill climb revisits the same optimum from several restarts, so
    // without this the "alternatives" list is five copies of the winner.
    const signature = selection.join(",");
    if (this.seen.has(signature)) {
      return;
    }
    if (this.entries.length >= this.capacity) {
      const worst = this.entries[this.entries.length - 1];
      if (evaluation.ev <= worst.evaluation.ev) {
        return;
      }
    }
    // Recorded only once a candidate makes the board, which keeps the set small
    // during an exhaustive enumeration of tens of thousands of loadouts.
    this.seen.add(signature);
    this.entries.push({ selection: selection.slice(), evaluation });
    this.entries.sort((a, b) => b.evaluation.ev - a.evaluation.ev);
    if (this.entries.length > this.capacity) {
      this.entries.length = this.capacity;
    }
  }

  /**
   * @returns The retained candidates, best first.
   */
  all(): readonly { selection: Selection; evaluation: QuickEvaluation }[] {
    return this.entries;
  }
}

/** Options controlling the search. */
export interface SearchOptions {
  /** Override the exhaustive/heuristic cutoff; used by tests. */
  readonly exhaustiveLimit?: number;
  /** Random restarts for the hill climb. */
  readonly restarts?: number;
  /** Seed for those restarts. */
  readonly seed?: number;
  /** How many runner-up sets to report. */
  readonly alternatives?: number;
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

/**
 * Enumerate every legal size-6 selection.
 *
 * @param groups - Pooled dice groups.
 * @param visit - Called once per complete selection.
 */
function enumerateAll(
  groups: readonly DiceGroup[],
  visit: (selection: Selection) => void,
): void {
  const selection: Selection = new Array<number>(groups.length).fill(0);

  const recurse = (index: number, remaining: number): void => {
    if (remaining === 0) {
      visit(selection);
      return;
    }
    if (index >= groups.length) {
      return;
    }
    const max = Math.min(groups[index].available, remaining);
    for (let take = max; take >= 0; take -= 1) {
      selection[index] = take;
      recurse(index + 1, remaining - take);
    }
    selection[index] = 0;
  };

  recurse(0, SET_SIZE);
}

/**
 * Multi-start hill climb over single-die swaps.
 *
 * Each restart begins from a legal selection and repeatedly tries moving one die
 * from one group to another, keeping any move that raises expected value, until
 * no single swap helps.
 *
 * @param groups - Pooled dice groups.
 * @param evaluate - Exact evaluator for a selection.
 * @param board - Leaderboard collecting the best selections seen.
 * @param options - Restart count and seed.
 */
function hillClimb(
  groups: readonly DiceGroup[],
  evaluate: (selection: Selection) => QuickEvaluation,
  board: Leaderboard,
  options: SearchOptions,
): void {
  const random = mulberry32(options.seed ?? 0x5eed);
  const restarts = options.restarts ?? 8;

  for (let restart = 0; restart < restarts; restart += 1) {
    // Restart 0 starts greedy (fill from the highest solo-EV group down); the
    // rest start from random legal selections to escape local optima.
    const selection =
      restart === 0 ? greedySeed(groups, evaluate) : randomSeed(groups, random);
    let current = evaluate(selection);
    board.offer(selection, current);

    // Steepest ascent: score every legal single-die swap against the *current*
    // selection, then apply only the best one and rescan. Applying swaps as they
    // are found while continuing to iterate would mutate the selection out from
    // under the loop bounds — an earlier version did exactly that and could
    // drive a group's count negative, producing seven-dice "sets" whose value
    // rises without limit and a search that never terminates.
    for (;;) {
      let bestMove: { from: number; to: number; evaluation: QuickEvaluation } | null = null;

      for (let from = 0; from < groups.length; from += 1) {
        if (selection[from] === 0) {
          continue;
        }
        for (let to = 0; to < groups.length; to += 1) {
          if (to === from || selection[to] >= groups[to].available) {
            continue;
          }
          selection[from] -= 1;
          selection[to] += 1;
          const candidate = evaluate(selection);
          selection[from] += 1;
          selection[to] -= 1;

          if (candidate.ev > current.ev && candidate.ev > (bestMove?.evaluation.ev ?? -Infinity)) {
            bestMove = { from, to, evaluation: candidate };
          }
        }
      }

      if (!bestMove) {
        break;
      }
      selection[bestMove.from] -= 1;
      selection[bestMove.to] += 1;
      current = bestMove.evaluation;
      board.offer(selection, current);
    }
  }
}

/**
 * Build a starting selection by taking as many of the best solo group as
 * allowed, then the next best, and so on.
 *
 * @param groups - Pooled dice groups.
 * @param evaluate - Exact evaluator, used here on single-group selections.
 * @returns A legal size-6 selection.
 */
function greedySeed(
  groups: readonly DiceGroup[],
  evaluate: (selection: Selection) => QuickEvaluation,
): Selection {
  const solo = groups.map((group, index) => {
    const probe: Selection = new Array<number>(groups.length).fill(0);
    const take = Math.min(group.available, SET_SIZE);
    probe[index] = take;
    // Per-die value, so a group that cannot fill all six slots is still
    // comparable with one that can.
    return { index, ev: evaluate(probe).ev / take };
  });
  solo.sort((a, b) => b.ev - a.ev);

  const selection: Selection = new Array<number>(groups.length).fill(0);
  let remaining = SET_SIZE;
  for (const { index } of solo) {
    if (remaining === 0) {
      break;
    }
    const take = Math.min(groups[index].available, remaining);
    selection[index] = take;
    remaining -= take;
  }
  return selection;
}

/**
 * Build a random legal starting selection.
 *
 * @param groups - Pooled dice groups.
 * @param random - Seeded random source.
 * @returns A legal size-6 selection.
 */
function randomSeed(groups: readonly DiceGroup[], random: () => number): Selection {
  const selection: Selection = new Array<number>(groups.length).fill(0);
  let remaining = SET_SIZE;
  while (remaining > 0) {
    const index = randomInt(random, groups.length);
    if (selection[index] < groups[index].available) {
      selection[index] += 1;
      remaining -= 1;
    }
  }
  return selection;
}
