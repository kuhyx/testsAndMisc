/**
 * The vocabulary the loadout search is expressed in: an inventory line, the
 * pooled groups it collapses to, and a per-group selection.
 *
 * Dice whose *scoring* behaviour is identical are merged before any search
 * runs. Nine of the game's dice are plain uniform 16.7% dice under different
 * names, and the three Painter's dice share one distribution, so pooling alone
 * removes a large amount of duplicate work.
 */

import type { Die } from "../data/dice.ts";
import { categoryWeights } from "./distribution.ts";

/** How many dice go into a loadout. */
export const SET_SIZE = 6;

/** One line of the user's inventory. */
export interface InventoryEntry {
  readonly die: Die;
  readonly count: number;
}

/** A group of dice that score identically, pooled into one searchable type. */
export interface DiceGroup {
  /** Representative die, used for evaluation. */
  readonly die: Die;
  /** Every die id in the group, so the UI can explain the substitution. */
  readonly members: readonly string[];
  /** Total number of interchangeable dice available across the group. */
  readonly available: number;
}

/** A candidate expressed as how many dice are taken from each group. */
export type Selection = number[];

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

/**
 * Expand a per-group selection into the concrete dice it stands for.
 *
 * @param groups - Pooled dice groups, in the same order as the selection.
 * @param selection - How many dice to take from each group.
 * @returns The six dice of the loadout.
 */
export function expand(groups: readonly DiceGroup[], selection: Selection): Die[] {
  const dice: Die[] = [];
  groups.forEach((group, index) => {
    for (let n = 0; n < selection[index]; n += 1) {
      dice.push(group.die);
    }
  });
  return dice;
}
