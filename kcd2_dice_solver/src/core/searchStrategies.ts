/**
 * The two ways the loadout search explores the space of size-6 selections, plus
 * the leaderboard that both feed.
 *
 *   enumerateAll  every size-6 multiset the inventory allows; provably optimal
 *   hillClimb     multi-start local search over single-die swaps; labelled as
 *                 heuristic in the result so it is never mistaken for a proof
 *
 * Which one runs is decided by problem size in `findBestSet`; neither knows
 * about that choice.
 */

import type { QuickEvaluation } from "./evaluate.ts";
import { SET_SIZE } from "./searchGroups.ts";
import type { DiceGroup, Selection } from "./searchGroups.ts";
import { mulberry32, randomInt } from "../lib/rng.ts";

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

/** Keeps the best few candidates seen, so the UI can show runners-up. */
export class Leaderboard {
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

/**
 * Enumerate every legal size-6 selection.
 *
 * @param groups - Pooled dice groups.
 * @param visit - Called once per complete selection.
 */
export function enumerateAll(
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
export function hillClimb(
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
