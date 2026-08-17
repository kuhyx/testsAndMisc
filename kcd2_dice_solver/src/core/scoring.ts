/**
 * Farkle scoring as played in Kingdom Come: Deliverance II.
 *
 * Transcribed from the scoring table at
 * https://kingdom-come-deliverance.fandom.com/wiki/Dice/KCD2:
 *
 *   each 1                 100
 *   each 5                  50
 *   three of a kind        1000 for ones, otherwise 100 * face
 *   each die beyond three  doubles the set's value
 *   straight 1-5            500
 *   straight 2-6            750
 *   straight 1-6           1500
 *
 * The wiki's "Four of a kind 400 / Five of a kind 800 / Six of a kind 1600" row
 * is the doubling rule illustrated on twos (200 -> 400 -> 800 -> 1600), which is
 * why it is expressed as a formula rather than a lookup.
 *
 * A roll's score is the best partition of its dice into combinations; dice left
 * over simply score nothing. That maximisation is what this file computes, over
 * the legal steps enumerated by `scoringMoves.ts` — which is also where the two
 * joker faces and their differing rules are handled.
 */

import type { ScoringRules, FormationValues } from "../data/badges.ts";
import { DEFAULT_FORMATION_VALUES } from "../data/badges.ts";
import { CATEGORIES, WILD_ALONE, WILD_COMBO, decode, encode } from "./counts.ts";
import type { CountVector } from "./counts.ts";
import { scoringMoves } from "./scoringMoves.ts";
import type { ScoringConfig } from "./scoringMoves.ts";

export { CATEGORIES, FACES, WILD_ALONE, WILD_COMBO } from "./counts.ts";
export type { CountVector } from "./counts.ts";

/** The two kinds of substitute die, for {@link Scorer.scoreFaces}. */
export interface WildCounts {
  /** Balatro jokers, which may also be held on their own as a 1. */
  readonly alone?: number;
  /** Devil's heads, which only count inside a combination. */
  readonly combo?: number;
}

/**
 * A memoised scorer bound to one rule set.
 *
 * The reachable state space is tiny (a few thousand count vectors), so the cache
 * is built lazily once per rule set and then reused across every candidate dice
 * set the search evaluates.
 */
export class Scorer {
  private readonly cache = new Map<number, number>();

  private readonly strictCache = new Map<number, number>();

  private readonly config: ScoringConfig;

  /**
   * @param rules - Which badge-granted scoring rules are active.
   * @param formationValues - Point values for the badge formations.
   */
  constructor(
    rules: ScoringRules,
    formationValues: FormationValues = DEFAULT_FORMATION_VALUES,
  ) {
    this.config = { rules, formationValues };
  }

  /**
   * Best achievable score for a roll.
   *
   * @param counts - Count vector of the roll (faces 1-6 plus wildcards).
   * @returns The maximum total over all legal partitions; 0 means a bust.
   */
  score(counts: CountVector): number {
    return this.scoreKey(encode(counts));
  }

  /**
   * Best achievable score for a roll already packed into a key.
   *
   * The hot path uses this: on a cache hit no count vector is ever materialised,
   * which is what keeps a full search in the tens of milliseconds.
   *
   * @param key - Packed count vector, see `counts.ts`.
   * @returns The maximum total over all legal partitions; 0 means a bust.
   */
  scoreKey(key: number): number {
    const hit = this.cache.get(key);
    if (hit !== undefined) {
      return hit;
    }
    const value = this.compute(decode(key));
    this.cache.set(key, value);
    return value;
  }

  /**
   * Score a plain list of face values, for tests and the simulator.
   *
   * @param faces - Face values rolled, each 1-6.
   * @param wilds - How many substitutes of each kind are in the roll.
   * @returns The best achievable score.
   */
  scoreFaces(faces: readonly number[], wilds: WildCounts = {}): number {
    const counts = new Array<number>(CATEGORIES).fill(0);
    for (const face of faces) {
      counts[face - 1] += 1;
    }
    counts[WILD_ALONE] = wilds.alone ?? 0;
    counts[WILD_COMBO] = wilds.combo ?? 0;
    return this.score(counts);
  }

  /**
   * Best score for a set of dice in which *every* die must be part of a
   * combination.
   *
   * This is what "holding" dice means in the mini-game: you may only set aside
   * dice that actually score, so a legal hold is exactly a sub-multiset with a
   * finite value here. The plain `score` cannot answer that, because it is free
   * to ignore dead dice.
   *
   * @param counts - Count vector of the dice being held.
   * @returns The best score using all of them, or `-Infinity` if impossible.
   */
  scoreUsingAll(counts: CountVector): number {
    const key = encode(counts);
    const hit = this.strictCache.get(key);
    if (hit !== undefined) {
      return hit;
    }
    const value = this.computeStrict(counts);
    this.strictCache.set(key, value);
    return value;
  }

  /**
   * Uncached recursion for {@link scoreUsingAll}.
   *
   * @param counts - Count vector of the remaining dice.
   * @returns Best score consuming every die, or `-Infinity`.
   */
  private computeStrict(counts: CountVector): number {
    const remaining = counts.reduce((sum, count) => sum + count, 0);
    if (remaining === 0) {
      return 0;
    }
    let best = -Infinity;
    for (const { value, rest } of scoringMoves(counts, this.config)) {
      const tail = this.scoreUsingAll(rest);
      if (tail > -Infinity) {
        best = Math.max(best, value + tail);
      }
    }
    return best;
  }

  /**
   * Uncached recursive maximisation over partitions.
   *
   * @param counts - Count vector of the remaining dice.
   * @returns The best score obtainable from those dice.
   */
  private compute(counts: CountVector): number {
    // Leaving dice unscored is always legal, so 0 is the floor.
    let best = 0;
    for (const { value, rest } of scoringMoves(counts, this.config)) {
      best = Math.max(best, value + this.score(rest));
    }
    return best;
  }
}
