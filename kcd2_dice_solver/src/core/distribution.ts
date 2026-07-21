/**
 * Exact outcome distribution for a set of loaded dice.
 *
 * Naively a six-dice set has 6^6 = 46,656 ordered outcomes, and the search
 * evaluates tens of thousands of candidate sets. But scoring depends only on the
 * *multiset* of faces, and the dice are independent, so we convolve them into a
 * distribution over count vectors instead. After six dice there are at most
 * C(12, 6) = 924 distinct count vectors — roughly fifty times less work, and,
 * unlike sampling, exact.
 *
 * The count vectors stay packed as integers throughout (see `counts.ts`), so a
 * convolution step is an integer addition and the scorer can look the result up
 * without ever building an array.
 */

import type { Die, Face } from "../data/dice.ts";
import { CATEGORIES, SLOT_STEP, WILD, decode } from "./counts.ts";

/** One reachable outcome: a count vector and the probability of reaching it. */
export interface Outcome {
  readonly counts: readonly number[];
  readonly probability: number;
}

/** The same distribution with count vectors left packed. */
export interface PackedDistribution {
  /** Packed count vectors, one per reachable outcome. */
  readonly keys: readonly number[];
  /** Probability of each, index-aligned with `keys`. Sums to 1. */
  readonly probabilities: readonly number[];
}

/**
 * Collapse a die's face weights into the seven scoring categories.
 *
 * Faces flagged as wildcards contribute their probability to the wildcard slot
 * rather than to their printed face, because that is how they score.
 *
 * @param die - The die to convert.
 * @returns A seven-element probability vector, faces 1-6 then wildcard.
 */
export function categoryWeights(die: Die): number[] {
  const weights = new Array<number>(CATEGORIES).fill(0);
  for (let face = 0; face < 6; face += 1) {
    const isWild = die.wildcardFaces.includes((face + 1) as Face);
    const slot = isWild ? WILD : face;
    weights[slot] += die.weights[face];
  }
  return weights;
}

/**
 * Drop the zero-probability categories from a die's weights.
 *
 * Several dice have a 0% face and the Pie die has two. Skipping them keeps the
 * convolution from branching into states that can never happen.
 *
 * @param weights - Category weights of one die.
 * @returns Key step and probability for each category the die can actually roll.
 */
function transitions(weights: readonly number[]): { step: number; weight: number }[] {
  const result: { step: number; weight: number }[] = [];
  for (let slot = 0; slot < CATEGORIES; slot += 1) {
    const weight = weights[slot];
    if (weight > 0) {
      result.push({ step: SLOT_STEP[slot], weight });
    }
  }
  return result;
}

/**
 * Convolve a set of dice into the exact distribution over packed count vectors.
 *
 * @param dice - The dice being rolled together, in any order.
 * @returns Packed keys with their probabilities, which sum to 1.
 */
export function packedDistribution(dice: readonly Die[]): PackedDistribution {
  let keys: number[] = [0];
  let probabilities: number[] = [1];

  for (const die of dice) {
    const steps = transitions(categoryWeights(die));
    const merged = new Map<number, number>();
    for (let i = 0; i < keys.length; i += 1) {
      const key = keys[i];
      const probability = probabilities[i];
      for (const { step, weight } of steps) {
        const nextKey = key + step;
        merged.set(nextKey, (merged.get(nextKey) ?? 0) + probability * weight);
      }
    }
    keys = [...merged.keys()];
    probabilities = [...merged.values()];
  }

  return { keys, probabilities };
}

/**
 * Convolve a set of dice into the exact distribution over count vectors.
 *
 * @param dice - The dice being rolled together, in any order.
 * @returns Every reachable outcome with its probability. Probabilities sum to 1.
 */
export function rollDistribution(dice: readonly Die[]): Outcome[] {
  const { keys, probabilities } = packedDistribution(dice);
  return keys.map((key, index) => ({
    counts: decode(key),
    probability: probabilities[index],
  }));
}
