/**
 * Ground truth for the search.
 *
 * The exhaustive path is checked against an independent brute-force enumeration,
 * and the heuristic path is checked against the exhaustive one on a problem
 * small enough that the true optimum is known.
 */

import { describe, expect, it } from "vitest";
import { BASE_RULES } from "../data/badges.ts";
import { DICE_BY_ID } from "../data/dice.ts";
import type { Die } from "../data/dice.ts";
import { evaluateQuick } from "./evaluate.ts";
import { Scorer } from "./scoring.ts";
import { SET_SIZE, countCandidates, findBestSet, groupInventory } from "./search.ts";
import type { InventoryEntry } from "./search.ts";

const die = (id: string): Die => {
  const found = DICE_BY_ID.get(id);
  if (!found) {
    throw new Error(`no such die: ${id}`);
  }
  return found;
};

/**
 * Best six-dice set by exhaustive enumeration, written independently of the
 * search's own combinatorics.
 *
 * @param inventory - Owned dice with counts.
 * @param scorer - Scorer to evaluate with.
 * @returns The best set's expected value.
 */
function bruteForceBest(inventory: readonly InventoryEntry[], scorer: Scorer): number {
  const pool: Die[] = [];
  for (const entry of inventory) {
    for (let n = 0; n < entry.count; n += 1) {
      pool.push(entry.die);
    }
  }

  let best = -Infinity;
  const choose = (start: number, picked: Die[]): void => {
    if (picked.length === SET_SIZE) {
      best = Math.max(best, evaluateQuick(picked, scorer).ev);
      return;
    }
    for (let i = start; i < pool.length; i += 1) {
      picked.push(pool[i]);
      choose(i + 1, picked);
      picked.pop();
    }
  };
  choose(0, []);
  return best;
}

describe("inventory grouping", () => {
  it("pools dice whose distributions are identical", () => {
    // Six of the game's dice are plain uniform 16.7% dice under different names.
    const groups = groupInventory([
      { die: die("ordinary"), count: 2 },
      { die: die("hugo"), count: 2 },
      { die: die("molar"), count: 1 },
    ]);
    expect(groups).toHaveLength(1);
    expect(groups[0].available).toBe(5);
    expect(groups[0].members).toEqual(["ordinary", "hugo", "molar"]);
  });

  it("keeps genuinely different dice apart", () => {
    const groups = groupInventory([
      { die: die("ordinary"), count: 1 },
      { die: die("weighted"), count: 1 },
    ]);
    expect(groups).toHaveLength(2);
  });

  it("ignores entries with no dice", () => {
    expect(groupInventory([{ die: die("ordinary"), count: 0 }])).toHaveLength(0);
  });

  it("caps a group at six, since a loadout is only six dice", () => {
    const groups = groupInventory([{ die: die("ordinary"), count: 99 }]);
    expect(groups[0].available).toBe(SET_SIZE);
  });
});

describe("candidate counting", () => {
  it("counts one loadout when exactly six dice are owned", () => {
    expect(countCandidates(groupInventory([{ die: die("ordinary"), count: 6 }]))).toBe(1);
  });

  it("counts every split between two groups", () => {
    // Six from each of two groups: 0/6, 1/5, ... 6/0 is seven loadouts.
    const groups = groupInventory([
      { die: die("ordinary"), count: 6 },
      { die: die("weighted"), count: 6 },
    ]);
    expect(countCandidates(groups)).toBe(7);
  });
});

describe("exhaustive search", () => {
  const scorer = new Scorer(BASE_RULES);

  it("matches an independent brute force", () => {
    const inventory: InventoryEntry[] = [
      { die: die("ordinary"), count: 2 },
      { die: die("weighted"), count: 2 },
      { die: die("grozav"), count: 2 },
      { die: die("misfortune"), count: 2 },
    ];
    const result = findBestSet(inventory, scorer);
    expect(result.optimal).toBe(true);
    expect(result.evaluation.ev).toBeCloseTo(bruteForceBest(inventory, scorer), 9);
  });

  it("reports distinct runner-up loadouts", () => {
    const result = findBestSet(
      [
        { die: die("ordinary"), count: 6 },
        { die: die("weighted"), count: 6 },
        { die: die("lucky"), count: 6 },
      ],
      scorer,
      { alternatives: 3 },
    );
    const signatures = [result, ...result.alternatives].map((entry) =>
      entry.dice
        .map((d) => d.id)
        .sort((a, b) => a.localeCompare(b))
        .join(","),
    );
    expect(new Set(signatures).size).toBe(signatures.length);
    // And they must be ordered worst-last.
    const values = result.alternatives.map((a) => a.evaluation.ev);
    expect(values).toEqual([...values].sort((a, b) => b - a));
    expect(result.evaluation.ev).toBeGreaterThanOrEqual(values[0]);
  });

  it("names the dice that were pooled into the pick", () => {
    const result = findBestSet(
      [
        { die: die("ordinary"), count: 3 },
        { die: die("hugo"), count: 3 },
      ],
      scorer,
    );
    expect(result.equivalentIds).toEqual(["ordinary", "hugo"]);
  });

  it("refuses an inventory smaller than a loadout", () => {
    expect(() => findBestSet([{ die: die("ordinary"), count: 5 }], scorer)).toThrow(
      /at least 6 dice/,
    );
  });
});

describe("heuristic search", () => {
  const scorer = new Scorer(BASE_RULES);

  const inventory: InventoryEntry[] = [
    { die: die("ordinary"), count: 6 },
    { die: die("weighted"), count: 6 },
    { die: die("grozav"), count: 6 },
    { die: die("misfortune"), count: 6 },
    { die: die("lucky"), count: 6 },
    { die: die("pie"), count: 6 },
    { die: die("monk"), count: 6 },
  ];

  it("finds the true optimum on a problem the exhaustive path can also solve", () => {
    const truth = findBestSet(inventory, scorer);
    expect(truth.optimal).toBe(true);

    // Same inventory, but forced down the hill-climb path.
    const heuristic = findBestSet(inventory, scorer, { exhaustiveLimit: 0 });
    expect(heuristic.optimal).toBe(false);
    expect(heuristic.evaluation.ev).toBeCloseTo(truth.evaluation.ev, 9);
  });

  it("stays within one percent of optimal from a single random restart", () => {
    const truth = findBestSet(inventory, scorer);
    for (const seed of [1, 2, 3, 12345]) {
      const heuristic = findBestSet(inventory, scorer, {
        exhaustiveLimit: 0,
        restarts: 1,
        seed,
      });
      expect(heuristic.evaluation.ev).toBeGreaterThan(truth.evaluation.ev * 0.99);
    }
  });

  it("always returns exactly six dice", () => {
    // The hill climb once drove a group's count negative and produced sets of
    // the wrong size; this pins the invariant.
    for (const seed of [0, 7, 99, 4242]) {
      const result = findBestSet(inventory, scorer, {
        exhaustiveLimit: 0,
        restarts: 3,
        seed,
      });
      expect(result.dice).toHaveLength(SET_SIZE);
      for (const alternative of result.alternatives) {
        expect(alternative.dice).toHaveLength(SET_SIZE);
      }
    }
  });

  it("respects how many of each die the player owns", () => {
    const result = findBestSet(
      [
        { die: die("weighted"), count: 2 },
        { die: die("ordinary"), count: 6 },
      ],
      scorer,
      { exhaustiveLimit: 0 },
    );
    const weighted = result.dice.filter((d) => d.id === "weighted");
    expect(weighted).toHaveLength(2);
  });
});
