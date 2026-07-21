/**
 * Exact single-roll evaluation of a dice set.
 *
 * This is the solver's default objective. It is policy-free: it asks only "if I
 * throw these six dice, what is the expected value of the best combination on
 * the table, and how often do I bust?". No push-your-luck assumptions are baked
 * in, so the number is a property of the dice rather than of a playstyle.
 *
 * Bust probability is reported alongside because expected value alone
 * over-rewards swingy sets — a set that busts a fifth of the time loses games
 * that its average score says it should win.
 *
 * Two entry points on purpose: the search runs `evaluateQuick` tens of thousands
 * of times and only needs the mean and the bust rate, while `evaluateSet` also
 * sorts the distribution for a percentile and is called a handful of times on
 * the results that are actually reported.
 */

import type { Die } from "../data/dice.ts";
import { packedDistribution } from "./distribution.ts";
import type { Scorer } from "./scoring.ts";

/** What the search needs: the mean and the downside. */
export interface QuickEvaluation {
  /** Expected best-combination score of a single throw of the whole set. */
  readonly ev: number;
  /** Probability the throw scores nothing at all. */
  readonly bustProbability: number;
}

export interface Evaluation extends QuickEvaluation {
  /**
   * 90th-percentile throw score. Badges you save for a good moment (Warlord,
   * Doppelganger) are worth what a *good* throw is worth, not an average one.
   */
  readonly p90: number;
}

/**
 * Evaluate a dice set exactly, without the percentile.
 *
 * @param dice - The dice thrown together, normally six of them.
 * @param scorer - Memoised scorer carrying the active badge rules.
 * @returns Expected score and bust probability for one throw.
 */
export function evaluateQuick(dice: readonly Die[], scorer: Scorer): QuickEvaluation {
  const { keys, probabilities } = packedDistribution(dice);
  let ev = 0;
  let bustProbability = 0;
  for (let i = 0; i < keys.length; i += 1) {
    const probability = probabilities[i];
    const score = scorer.scoreKey(keys[i]);
    ev += probability * score;
    if (score === 0) {
      bustProbability += probability;
    }
  }
  return { ev, bustProbability };
}

/**
 * Evaluate a dice set exactly, including the 90th-percentile throw score.
 *
 * @param dice - The dice thrown together, normally six of them.
 * @param scorer - Memoised scorer carrying the active badge rules.
 * @returns Expected score, bust probability, and the 90th-percentile score.
 */
export function evaluateSet(dice: readonly Die[], scorer: Scorer): Evaluation {
  const { keys, probabilities } = packedDistribution(dice);
  let ev = 0;
  let bustProbability = 0;
  const outcomes: { score: number; probability: number }[] = [];

  for (let i = 0; i < keys.length; i += 1) {
    const probability = probabilities[i];
    const score = scorer.scoreKey(keys[i]);
    ev += probability * score;
    if (score === 0) {
      bustProbability += probability;
    }
    outcomes.push({ score, probability });
  }

  return { ev, bustProbability, p90: percentile(outcomes, 0.9) };
}

/** A score distribution you can take arbitrary percentiles of. */
export interface ScoreDistribution {
  /** Exact percentile of the single-throw score, for a fraction in [0, 1]. */
  readonly at: (fraction: number) => number;
}

/**
 * Build the exact single-throw score distribution of a dice set.
 *
 * @param dice - The dice thrown together.
 * @param scorer - Memoised scorer carrying the active badge rules.
 * @returns A distribution supporting percentile queries.
 */
export function scoreDistribution(
  dice: readonly Die[],
  scorer: Scorer,
): ScoreDistribution {
  const { keys, probabilities } = packedDistribution(dice);
  const outcomes = keys.map((key, index) => ({
    score: scorer.scoreKey(key),
    probability: probabilities[index],
  }));
  outcomes.sort((a, b) => a.score - b.score);
  return { at: (fraction) => percentile(outcomes, fraction) };
}

/**
 * Exact percentile of a discrete score distribution.
 *
 * @param outcomes - Score/probability pairs; probabilities must sum to 1.
 * @param fraction - Percentile to take, in [0, 1].
 * @returns The smallest score whose cumulative probability reaches `fraction`.
 */
export function percentile(
  outcomes: readonly { score: number; probability: number }[],
  fraction: number,
): number {
  const sorted = outcomes.toSorted((a, b) => a.score - b.score);
  let cumulative = 0;
  let last = 0;
  for (const outcome of sorted) {
    cumulative += outcome.probability;
    last = outcome.score;
    if (cumulative >= fraction) {
      return outcome.score;
    }
  }
  // Only reached when the probabilities sum below `fraction`, i.e. an empty or
  // truncated distribution; the largest score seen is the honest answer.
  return last;
}
