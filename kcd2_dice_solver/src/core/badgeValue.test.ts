/**
 * Tests for badge valuation.
 *
 * Every figure here is an estimate built on the simulator's stated policy, so
 * these tests assert the *properties* the model must have — an optional badge
 * can never be worth less than nothing, a bigger tier is worth at least as much
 * as a smaller one — rather than pinning arbitrary point totals.
 */

import { describe, expect, it } from "vitest";
import { BADGES_BY_ID, DEFAULT_FORMATION_VALUES } from "../data/badges.ts";
import type { Badge } from "../data/badges.ts";
import { DICE_BY_ID } from "../data/dice.ts";
import type { Die } from "../data/dice.ts";
import {
  bestThrowsValue,
  measureBaseline,
  rankValue,
  recommendBadges,
  singleCharge,
  valueBadge,
} from "./badgeValue.ts";
import type { BadgeContext } from "./badgeValue.ts";
import { NO_CHARGES, DEFAULT_POLICY } from "./simulate.ts";
import type { InventoryEntry } from "./search.ts";

const die = (id: string): Die => {
  const found = DICE_BY_ID.get(id);
  if (!found) {
    throw new Error(`no such die: ${id}`);
  }
  return found;
};

const badge = (id: string): Badge => {
  const found = BADGES_BY_ID.get(id);
  if (!found) {
    throw new Error(`no such badge: ${id}`);
  }
  return found;
};

const inventory: InventoryEntry[] = [
  { die: die("ordinary"), count: 6 },
  { die: die("lucky"), count: 6 },
  { die: die("weighted"), count: 2 },
];

const context: BadgeContext = {
  inventory,
  baselineDice: new Array<Die>(6).fill(die("ordinary")),
  formationValues: DEFAULT_FORMATION_VALUES,
  policy: DEFAULT_POLICY,
  seed: 0x5eed,
  searchOptions: {},
};

const baseline = measureBaseline(context);

describe("measureBaseline", () => {
  it("measures the loadout once, for every badge to share", () => {
    expect(baseline.turn).toBeGreaterThan(0);
    expect(baseline.ev).toBeGreaterThan(0);
    expect(baseline.throwsPerTurn).toBeGreaterThanOrEqual(1);
    expect(baseline.p90).toBeGreaterThan(0);
    expect(baseline.distribution.at(0.9)).toBe(baseline.p90);
  });
});

describe("bestThrowsValue", () => {
  const distribution = { at: (fraction: number): number => fraction * 1000 };

  it("values later charges at lower percentiles", () => {
    // One charge is worth the best throw; three charges are worth the best
    // three, which is less than three times the best.
    const one = bestThrowsValue(distribution, 1, 10);
    const three = bestThrowsValue(distribution, 3, 10);
    expect(three).toBeGreaterThan(one);
    expect(three).toBeLessThan(one * 3);
  });

  it("never dips below the median, however short the game", () => {
    expect(bestThrowsValue(distribution, 1, 1)).toBe(500);
  });

  it("is zero for a badge with no charges", () => {
    expect(bestThrowsValue(distribution, 0, 10)).toBe(0);
  });
});

describe("singleCharge", () => {
  it("maps each simulated effect onto one charge", () => {
    expect(singleCharge(badge("tin_might"))).toEqual({ ...NO_CHARGES, extraDice: 1 });
    expect(singleCharge(badge("tin_resurrection"))).toEqual({ ...NO_CHARGES, antibust: 1 });
    expect(singleCharge(badge("gold_fortune"))).toEqual({
      ...NO_CHARGES,
      reroll: 1,
      rerollDice: 3,
    });
    expect(singleCharge(badge("gold_transmutation"))).toEqual({
      ...NO_CHARGES,
      setDie: 1,
      setDieValue: 1,
    });
  });

  it("gives no charges to badges that are valued analytically", () => {
    expect(singleCharge(badge("gold_warlord"))).toEqual(NO_CHARGES);
    expect(singleCharge(badge("gold_headstart"))).toEqual(NO_CHARGES);
  });
});

describe("valueBadge", () => {
  it("never values an optional badge below zero", () => {
    // A badge you may simply decline to use cannot cost you points, so a
    // negative estimate would be a modelling error, not a finding.
    for (const id of BADGES_BY_ID.keys()) {
      const valuation = valueBadge(badge(id), context, baseline);
      if (valuation.pointsPerGame !== null) {
        expect(valuation.pointsPerGame).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("gives every badge a stated reason", () => {
    for (const id of BADGES_BY_ID.keys()) {
      expect(valueBadge(badge(id), context, baseline).reason.length).toBeGreaterThan(10);
    }
  });

  it("reports defence badges as situational rather than inventing a number", () => {
    const valuation = valueBadge(badge("gold_defence"), context, baseline);
    expect(valuation.pointsPerGame).toBeNull();
    expect(valuation.reason).toMatch(/situational/i);
  });

  it("values headstart at exactly its point lead", () => {
    expect(valueBadge(badge("tin_headstart"), context, baseline).pointsPerGame).toBe(250);
    expect(valueBadge(badge("gold_headstart"), context, baseline).pointsPerGame).toBe(1000);
  });

  it("ranks a higher tier at least as high as a lower one", () => {
    const tin = valueBadge(badge("tin_might"), context, baseline).pointsPerGame ?? 0;
    const gold = valueBadge(badge("gold_might"), context, baseline).pointsPerGame ?? 0;
    expect(gold).toBeGreaterThanOrEqual(tin);
  });

  it("returns a re-optimised loadout for scoring badges only", () => {
    expect(valueBadge(badge("gold_emperors"), context, baseline).dice).toHaveLength(6);
    expect(valueBadge(badge("gold_might"), context, baseline).dice).toBeNull();
  });

  it("measures its own baseline when not given one", () => {
    const valuation = valueBadge(badge("tin_headstart"), context);
    expect(valuation.pointsPerGame).toBe(250);
  });
});

describe("rankValue", () => {
  it("ranks a scored badge by its points", () => {
    expect(
      rankValue({ badge: badge("tin_headstart"), pointsPerGame: 250, reason: "", dice: null }),
    ).toBe(250);
  });

  it("sinks a situational badge below every scored one", () => {
    expect(
      rankValue({ badge: badge("tin_defence"), pointsPerGame: null, reason: "", dice: null }),
    ).toBe(-Infinity);
  });
});

describe("recommendBadges", () => {
  it("returns one ranked list per owned tier", () => {
    const recommendations = recommendBadges(
      new Set(["tin_might", "tin_headstart", "gold_warlord"]),
      context,
    );
    expect(recommendations.map((r) => r.tier)).toEqual(["tin", "gold"]);
    expect(recommendations[0].ranked).toHaveLength(2);
    expect(recommendations[1].ranked).toHaveLength(1);
  });

  it("orders each tier best first", () => {
    const [tin] = recommendBadges(
      new Set(["tin_might", "tin_headstart", "tin_fortune", "tin_defence"]),
      context,
    );
    const values = tin.ranked.map((v) => v.pointsPerGame ?? -Infinity);
    expect(values).toEqual([...values].sort((a, b) => b - a));
    // The situational defence badge sorts last rather than being dropped.
    expect(tin.ranked[tin.ranked.length - 1].badge.id).toBe("tin_defence");
  });

  it("returns nothing when no badges are owned", () => {
    expect(recommendBadges(new Set(), context)).toEqual([]);
  });
});
