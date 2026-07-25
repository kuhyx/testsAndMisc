/**
 * Tests for the solver entrypoint: inventory in, recommendation out.
 */

import { describe, expect, it } from "vitest";
import { DEFAULT_FORMATION_VALUES } from "../data/badges.ts";
import { DEFAULT_POLICY } from "./simulate.ts";
import { solve, toInventory } from "./solve.ts";

describe("toInventory", () => {
  it("resolves known die ids", () => {
    const entries = toInventory({ weighted: 2 });
    expect(entries).toHaveLength(1);
    expect(entries[0].die.name).toBe("Weighted die");
    expect(entries[0].count).toBe(2);
  });

  it("drops ids that are not dice in the game", () => {
    // A saved inventory from an older build could name a die that no longer
    // exists; that must not crash the solve.
    expect(toInventory({ not_a_real_die: 4 })).toHaveLength(0);
  });

  it("drops entries with no dice", () => {
    expect(toInventory({ weighted: 0 })).toHaveLength(0);
    expect(toInventory({ weighted: -3 })).toHaveLength(0);
  });
});

describe("solve", () => {
  it("fills in every default when only an inventory is given", () => {
    const result = solve({ diceCounts: { ordinary: 6 }, badgeIds: [] });
    expect(result.dice).toHaveLength(6);
    expect(result.simulation.turns).toBeGreaterThan(1000);
    expect(result.inventorySize).toBe(6);
    expect(result.badges).toEqual([]);
  });

  it("accepts explicit settings", () => {
    const result = solve({
      diceCounts: { ordinary: 6, weighted: 6 },
      badgeIds: ["tin_headstart"],
      formationValues: DEFAULT_FORMATION_VALUES,
      policy: DEFAULT_POLICY,
      simulationTurns: 500,
      searchOptions: { alternatives: 2 },
    });
    expect(result.simulation.turns).toBe(500);
    expect(result.alternatives).toHaveLength(2);
    expect(result.badges).toHaveLength(1);
    expect(result.badges[0].tier).toBe("tin");
  });

  it("echoes the inventory size back for the status line", () => {
    const result = solve({
      diceCounts: { ordinary: 4, weighted: 3, lucky: 2 },
      badgeIds: [],
      simulationTurns: 200,
    });
    expect(result.inventorySize).toBe(9);
  });

  it("solves an inventory containing both substitute dice", () => {
    // Each of the two joker faces takes its own path through the scorer and the
    // simulator's sampler, and this inventory exercises both at once.
    const result = solve({
      diceCounts: { balatro: 3, devils_head: 3, ordinary: 6 },
      badgeIds: [],
      simulationTurns: 500,
    });
    expect(result.dice).toHaveLength(6);
    expect(result.simulation.meanPerTurn).toBeGreaterThan(0);
    // Both substitute dice are uniform with the one replaced by a joker, so each
    // is strictly better than an ordinary die and all six get taken. Balatro's is
    // the better of the two — its joker can also be held on its own — but with
    // only three of each that never has to be decided.
    expect(result.dice.filter((die) => die.id === "ordinary")).toHaveLength(0);
    expect(result.dice.filter((die) => die.id === "balatro")).toHaveLength(3);
    expect(result.dice.filter((die) => die.id === "devils_head")).toHaveLength(3);
  });

  it("ties the two substitute dice on a single throw", () => {
    // Both are uniform with the one replaced by a joker, so on one throw of six
    // they are worth exactly the same: with five other dice there is always some
    // combination for a substitute to join, and the joker's extra "may be held
    // alone" only pays off later in a turn, once dice have been set aside.
    const balatro = solve({ diceCounts: { balatro: 6 }, badgeIds: [], simulationTurns: 200 });
    const devil = solve({ diceCounts: { devils_head: 6 }, badgeIds: [], simulationTurns: 200 });
    expect(balatro.evaluation.ev).toBeCloseTo(devil.evaluation.ev, 9);
  });
});
