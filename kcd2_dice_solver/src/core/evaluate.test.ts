/**
 * Cross-checks for the convolution.
 *
 * The whole speed story — packed integer keys, pooling identical dice, skipping
 * zero-weight faces, routing wildcards into a seventh slot — is exactly the kind
 * of optimisation that can produce subtly wrong probabilities while still
 * looking plausible. So the distribution is checked against a naive enumeration
 * of all 6^6 ordered outcomes, which shares none of that machinery.
 */

import { describe, expect, it } from "vitest";
import { BASE_RULES } from "../data/badges.ts";
import { DICE, DICE_BY_ID } from "../data/dice.ts";
import type { Die } from "../data/dice.ts";
import { CATEGORIES, WILD } from "./counts.ts";
import { categoryWeights, packedDistribution, rollDistribution } from "./distribution.ts";
import { evaluateQuick, evaluateSet, percentile, scoreDistribution } from "./evaluate.ts";
import { Scorer } from "./scoring.ts";

/**
 * Expected score and bust probability by brute-force enumeration.
 *
 * Walks all 6^n ordered face combinations directly, with no packing, no pooling
 * and no zero-weight pruning — deliberately the slow, obvious implementation.
 *
 * @param dice - The dice thrown together.
 * @param scorer - Scorer to evaluate each outcome with.
 * @returns Expected score and bust probability.
 */
function bruteForce(
  dice: readonly Die[],
  scorer: Scorer,
): { ev: number; bustProbability: number } {
  const weights = dice.map(categoryWeights);
  let ev = 0;
  let bustProbability = 0;

  const walk = (index: number, counts: number[], probability: number): void => {
    if (index === dice.length) {
      const score = scorer.score(counts);
      ev += probability * score;
      if (score === 0) {
        bustProbability += probability;
      }
      return;
    }
    for (let slot = 0; slot < CATEGORIES; slot += 1) {
      const weight = weights[index][slot];
      if (weight === 0) {
        continue;
      }
      counts[slot] += 1;
      walk(index + 1, counts, probability * weight);
      counts[slot] -= 1;
    }
  };

  walk(0, new Array<number>(CATEGORIES).fill(0), 1);
  return { ev, bustProbability };
}

const die = (id: string): Die => {
  const found = DICE_BY_ID.get(id);
  if (!found) {
    throw new Error(`no such die: ${id}`);
  }
  return found;
};

describe("convolution vs brute force", () => {
  const scorer = new Scorer(BASE_RULES);

  it("agrees on six identical fair dice", () => {
    const set = new Array<Die>(6).fill(die("ordinary"));
    const expected = bruteForce(set, scorer);
    const actual = evaluateQuick(set, scorer);
    expect(actual.ev).toBeCloseTo(expected.ev, 9);
    expect(actual.bustProbability).toBeCloseTo(expected.bustProbability, 9);
  });

  it("agrees on six different loaded dice", () => {
    const set = [
      die("weighted"),
      die("grozav"),
      die("favourable"),
      die("mathematician"),
      die("wagoner"),
      die("lucky"),
    ];
    const expected = bruteForce(set, scorer);
    const actual = evaluateQuick(set, scorer);
    expect(actual.ev).toBeCloseTo(expected.ev, 9);
    expect(actual.bustProbability).toBeCloseTo(expected.bustProbability, 9);
  });

  it("agrees on dice with zero-probability faces", () => {
    // Pie die has 0% fives and 0% sixes; Favourable die has 0% twos. These are
    // the faces the convolution prunes, so they need explicit cover.
    const set = [
      die("pie"),
      die("pie"),
      die("pie"),
      die("favourable"),
      die("favourable"),
      die("favourable"),
    ];
    const expected = bruteForce(set, scorer);
    const actual = evaluateQuick(set, scorer);
    expect(actual.ev).toBeCloseTo(expected.ev, 9);
    expect(actual.bustProbability).toBeCloseTo(expected.bustProbability, 9);
  });

  it("agrees on a mix including both wildcard dice", () => {
    const set = [
      die("balatro"),
      die("devils_head"),
      die("devils_head"),
      die("ordinary"),
      die("weighted"),
      die("pie"),
    ];
    const expected = bruteForce(set, scorer);
    const actual = evaluateQuick(set, scorer);
    expect(actual.ev).toBeCloseTo(expected.ev, 9);
    expect(actual.bustProbability).toBeCloseTo(expected.bustProbability, 9);
  });
});

describe("distribution mechanics", () => {
  it("produces probabilities that sum to one", () => {
    for (const target of DICE) {
      const { probabilities } = packedDistribution(new Array<Die>(6).fill(target));
      const total = probabilities.reduce((sum, value) => sum + value, 0);
      expect(total).toBeCloseTo(1, 12);
    }
  });

  it("routes wildcard faces into the wildcard slot", () => {
    const weights = categoryWeights(die("devils_head"));
    // The devil's head replaces the one, so face 1 must be empty.
    expect(weights[0]).toBe(0);
    expect(weights[WILD]).toBeCloseTo(1 / 6, 9);
  });

  it("routes every Balatro face into the wildcard slot", () => {
    const weights = categoryWeights(die("balatro"));
    expect(weights[WILD]).toBeCloseTo(1, 12);
  });

  it("decodes count vectors that sum to the number of dice", () => {
    const outcomes = rollDistribution(new Array<Die>(3).fill(die("ordinary")));
    for (const outcome of outcomes) {
      const total = outcome.counts.reduce((sum, value) => sum + value, 0);
      expect(total).toBe(3);
    }
  });
});

describe("percentiles", () => {
  const scorer = new Scorer(BASE_RULES);

  it("returns the smallest score reaching the cumulative fraction", () => {
    const outcomes = [
      { score: 0, probability: 0.5 },
      { score: 100, probability: 0.3 },
      { score: 900, probability: 0.2 },
    ];
    expect(percentile(outcomes, 0.4)).toBe(0);
    expect(percentile(outcomes, 0.7)).toBe(100);
    expect(percentile(outcomes, 0.9)).toBe(900);
  });

  it("falls back to the largest score when probabilities fall short", () => {
    // A truncated distribution summing below the requested fraction.
    expect(percentile([{ score: 700, probability: 0.5 }], 0.9)).toBe(700);
  });

  it("returns zero for an empty distribution", () => {
    expect(percentile([], 0.5)).toBe(0);
  });

  it("exposes the same percentile through scoreDistribution", () => {
    const set = new Array<Die>(6).fill(die("ordinary"));
    const distribution = scoreDistribution(set, scorer);
    expect(distribution.at(0.9)).toBe(evaluateSet(set, scorer).p90);
  });
});
