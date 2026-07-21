/**
 * Guards on the transcribed game data.
 *
 * The wiki publishes percentages rounded to one decimal place, so nothing here
 * sums to exactly 100 before normalisation. These tests make sure the
 * normalisation actually happened and that nothing was dropped in transcription.
 */

import { describe, expect, it } from "vitest";
import {
  BADGES,
  BADGES_BY_ID,
  BASE_RULES,
  DEFAULT_FORMATION_VALUES,
  HEADSTART_POINTS,
  TIERS,
} from "./badges.ts";
import { DICE, DICE_BY_ID, normalise } from "./dice.ts";

describe("dice data", () => {
  it("has all 43 dice from the wiki", () => {
    expect(DICE).toHaveLength(43);
  });

  it("normalises every distribution to sum to one", () => {
    for (const die of DICE) {
      const total = die.weights.reduce((sum, weight) => sum + weight, 0);
      expect(total).toBeCloseTo(1, 12);
    }
  });

  it("has no negative weights", () => {
    for (const die of DICE) {
      for (const weight of die.weights) {
        expect(weight).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("uses unique ids and names", () => {
    expect(new Set(DICE.map((die) => die.id)).size).toBe(DICE.length);
    expect(new Set(DICE.map((die) => die.name)).size).toBe(DICE.length);
  });

  it("indexes every die by id", () => {
    expect(DICE_BY_ID.size).toBe(DICE.length);
    expect(DICE_BY_ID.get("weighted")?.name).toBe("Weighted die");
    expect(DICE_BY_ID.get("nope")).toBeUndefined();
  });

  it("is sorted by display name", () => {
    const names = DICE.map((die) => die.name);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
  });

  it("marks exactly the two wildcard dice", () => {
    const wild = DICE.filter((die) => die.wildcardFaces.length > 0);
    expect(wild.map((die) => die.id).sort((a, b) => a.localeCompare(b))).toEqual([
      "balatro",
      "devils_head",
    ]);
    expect(DICE_BY_ID.get("devils_head")?.wildcardFaces).toEqual([1]);
    expect(DICE_BY_ID.get("balatro")?.wildcardFaces).toHaveLength(6);
  });

  it("keeps the dice with a zero-probability face", () => {
    // Favourable die never rolls a 2; Pie die never rolls a 5 or a 6.
    expect(DICE_BY_ID.get("favourable")?.weights[1]).toBe(0);
    expect(DICE_BY_ID.get("pie")?.weights[4]).toBe(0);
    expect(DICE_BY_ID.get("pie")?.weights[5]).toBe(0);
  });

  it("normalises a raw weight vector", () => {
    expect(normalise([1, 1, 1, 1, 1, 1])).toEqual([
      1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6,
    ]);
  });
});

describe("badge data", () => {
  it("has all 33 badges from the wiki", () => {
    expect(BADGES).toHaveLength(33);
  });

  it("uses unique ids and names", () => {
    expect(new Set(BADGES.map((badge) => badge.id)).size).toBe(BADGES.length);
    expect(new Set(BADGES.map((badge) => badge.name)).size).toBe(BADGES.length);
  });

  it("indexes every badge by id", () => {
    expect(BADGES_BY_ID.size).toBe(BADGES.length);
    expect(BADGES_BY_ID.get("gold_emperors")?.tier).toBe("gold");
  });

  it("assigns every badge to a known tier", () => {
    for (const badge of BADGES) {
      expect(TIERS).toContain(badge.tier);
    }
  });

  it("gives every tier a defence badge", () => {
    for (const tier of TIERS) {
      const defence = BADGES.filter(
        (badge) => badge.tier === tier && badge.effect.kind === "defence",
      );
      expect(defence).toHaveLength(1);
    }
  });

  it("has the five scoring badges", () => {
    const scoring = BADGES.filter((badge) => badge.effect.kind === "scoring");
    expect(scoring.map((badge) => badge.id).sort((a, b) => a.localeCompare(b))).toEqual([
      "carpenters_advantage",
      "executioners_advantage",
      "gold_emperors",
      "gold_tyche",
      "priests_advantage",
    ]);
  });

  it("wires the headstart badges to their tier's point lead", () => {
    for (const tier of TIERS) {
      const badge = BADGES.find(
        (candidate) => candidate.tier === tier && candidate.effect.kind === "headstart",
      );
      expect(badge?.effect).toEqual({ kind: "headstart", points: HEADSTART_POINTS[tier] });
    }
  });

  it("starts from a rule set with every scoring badge off", () => {
    expect(Object.values(BASE_RULES).every((value) => value === false)).toBe(true);
  });

  it("exposes editable formation values", () => {
    expect(DEFAULT_FORMATION_VALUES.cut).toBeGreaterThan(0);
    expect(DEFAULT_FORMATION_VALUES.gallows).toBeGreaterThan(0);
    expect(DEFAULT_FORMATION_VALUES.eye).toBeGreaterThan(0);
  });
});
