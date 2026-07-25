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
 * why it is expressed here as a formula rather than a lookup.
 *
 * A roll's score is the best partition of its dice into combinations; dice left
 * over simply score nothing. That maximisation is what `bestScore` computes.
 *
 * Two dice carry a joker face, and the wiki gives them *different* rules:
 *
 *   Devil's head  "acts as a joker, matching any combination but never scoring
 *                  on its own"
 *   Balatro       "you can choose how it's counted; it can fit into a straight
 *                  or a triple. Picking it alone will count as if you threw 1"
 *
 * So a Balatro joker is a free choice of face, while a Devil's head may only be
 * spent inside a multi-die combination — it can never be the single 1 or 5 that
 * lets you hold a die. Hence the two substitute slots in `counts.ts`.
 *
 * Both are allowed to fill in for *any* face of a combination, including cases
 * where every die of the combination is a substitute (three Devil's heads make a
 * triple). The wiki's examples all pair a joker with natural dice and it does not
 * say whether an all-joker set counts, so this is an assumption; it is the same
 * assumption the substitution rule makes everywhere else.
 */

import type { ScoringRules, FormationValues } from "../data/badges.ts";
import { DEFAULT_FORMATION_VALUES } from "../data/badges.ts";
import { CATEGORIES, FACES, WILD_ALONE, WILD_COMBO, decode, encode } from "./counts.ts";
import type { CountVector } from "./counts.ts";

export { CATEGORIES, FACES, WILD_ALONE, WILD_COMBO } from "./counts.ts";
export type { CountVector } from "./counts.ts";

/**
 * Base value of a three-of-a-kind of the given face.
 *
 * @param face - Die face, 1-6.
 * @returns 1000 for ones, otherwise 100 times the face value.
 */
export function tripleBase(face: number): number {
  return face === 1 ? 1000 : face * 100;
}

/**
 * Value of an n-of-a-kind, applying the "each additional die doubles" rule.
 *
 * @param face - Die face, 1-6.
 * @param n - How many dice of that face are used, must be at least 3.
 * @returns The combination's point value.
 */
export function ofAKindValue(face: number, n: number): number {
  return tripleBase(face) * 2 ** (n - 3);
}

/** The two kinds of substitute die, for {@link Scorer.scoreFaces}. */
export interface WildCounts {
  /** Balatro jokers, which may also be held on their own as a 1. */
  readonly alone?: number;
  /** Devil's heads, which only count inside a combination. */
  readonly combo?: number;
}

/** Everything `bestScore` needs beyond the roll itself. */
export interface ScoringConfig {
  readonly rules: ScoringRules;
  readonly formationValues: FormationValues;
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
    for (const { value, rest } of this.moves(counts)) {
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
    for (const { value, rest } of this.moves(counts)) {
      best = Math.max(best, value + this.score(rest));
    }
    return best;
  }

  /**
   * Every legal single step from a position: take one combination (or resolve
   * one Balatro joker) and hand the leftovers back to the recursion.
   *
   * Both scorers share this so the rules are stated exactly once.
   *
   * @param counts - Count vector of the remaining dice.
   * @returns Each move's point value and the dice left afterwards.
   */
  private moves(counts: CountVector): { value: number; rest: number[] }[] {
    const alone = counts[WILD_ALONE];
    if (alone > 0) {
      // A Balatro joker is a free choice of face — including a lone 1 — so it
      // can simply be resolved into each face and scored as that face from then
      // on. Resolving one at a time is sufficient: further jokers are handled by
      // the recursive call, and every assignment is reachable that way.
      const options: { value: number; rest: number[] }[] = [];
      for (let face = 0; face < FACES; face += 1) {
        const rest = counts.slice();
        rest[WILD_ALONE] = alone - 1;
        rest[face] += 1;
        options.push({ value: 0, rest });
      }
      return options;
    }

    const options: { value: number; rest: number[] }[] = [];
    const { rules, formationValues } = this.config;
    // Devil's heads cannot be resolved the same way: once one became a plain
    // face, nothing would stop it being held as a lone 1. They are instead spent
    // inside the combination they complete, which is what `take` below does.
    const substitutes = counts[WILD_COMBO];

    /**
     * Add every way of forming one combination out of distinct faces.
     *
     * Each required face is supplied either by a natural die or by a Devil's
     * head, and each choice leaves a different remainder, so all of them are
     * offered to the recursion.
     *
     * @param faces - The faces the combination needs, each at most once.
     * @param value - What the combination scores.
     */
    const take = (faces: readonly number[], value: number): void => {
      const rest = counts.slice();
      if (substitutes === 0) {
        // The common case by far — most hands hold no Devil's head at all — and
        // worth its own branch: it is one pass with no recursion and no second
        // copy of the vector, which is what keeps a full search fast.
        for (const face of faces) {
          if (rest[face - 1] === 0) {
            return;
          }
          rest[face - 1] -= 1;
        }
        options.push({ value, rest });
        return;
      }
      const fill = (index: number): void => {
        if (index === faces.length) {
          options.push({ value, rest: rest.slice() });
          return;
        }
        const slot = faces[index] - 1;
        if (rest[slot] > 0) {
          rest[slot] -= 1;
          fill(index + 1);
          rest[slot] += 1;
        }
        if (rest[WILD_COMBO] > 0) {
          rest[WILD_COMBO] -= 1;
          fill(index + 1);
          rest[WILD_COMBO] += 1;
        }
      };
      fill(0);
    };

    // Straights.
    take([1, 2, 3, 4, 5, 6], 1500);
    take([2, 3, 4, 5, 6], 750);
    take([1, 2, 3, 4, 5], 500);

    // Badge formations.
    if (rules.cut) {
      take([3, 5], formationValues.cut);
    }
    if (rules.gallows) {
      take([4, 5, 6], formationValues.gallows);
    }
    if (rules.eye) {
      take([1, 3, 5], formationValues.eye);
    }

    // N-of-a-kind, for every face and every usable size. Counting substitutes
    // by how many are spent rather than by which position they fill keeps this
    // free of duplicate moves, which `take` cannot avoid for repeated faces.
    for (let face = 0; face < FACES; face += 1) {
      const available = counts[face];
      for (let n = 3; n <= available + substitutes; n += 1) {
        for (let spent = Math.max(0, n - available); spent <= Math.min(substitutes, n); spent += 1) {
          const rest = counts.slice();
          rest[face] = available - (n - spent);
          rest[WILD_COMBO] = substitutes - spent;
          options.push({ value: this.combinationValue(face + 1, n), rest });
        }
      }
    }

    // Singles: only a natural one or five scores on its own. A Devil's head
    // deliberately has no move here — that is the whole of "never scoring on its
    // own", and it is why a lone one cannot be held.
    const takeSingle = (face: number, value: number): void => {
      if (counts[face - 1] > 0) {
        const rest = counts.slice();
        rest[face - 1] -= 1;
        options.push({ value, rest });
      }
    };
    takeSingle(1, 100);
    takeSingle(5, 50);

    return options;
  }

  /**
   * Value of an n-of-a-kind under the active badge rules.
   *
   * @param face - Die face, 1-6.
   * @param n - Number of dice in the set.
   * @returns The point value, including the Emperor and Tyche multipliers.
   */
  private combinationValue(face: number, n: number): number {
    const base = ofAKindValue(face, n);
    // Both badges name a specific three-die combination — "every 1+1+1" and
    // "three sixes" — so they multiply the triple only, not the four-, five- and
    // six-of-a-kind extensions of it. Applying the multiplier to those too made
    // the Emperor badge look like a 27,000-point swing in a game played to a few
    // thousand. The partition search still considers splitting six ones into two
    // tripled triples, so the better reading wins on its own merits.
    if (n === 3 && face === 1 && this.config.rules.emperorTriple) {
      return base * 3;
    }
    if (n === 3 && face === 6 && this.config.rules.tycheDouble) {
      return base * 2;
    }
    return base;
  }
}
