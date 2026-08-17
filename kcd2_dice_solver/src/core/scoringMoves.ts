/**
 * The move generator behind Farkle scoring: every legal single step from a
 * position, which `Scorer` maximises over.
 *
 * A step is either taking one combination — a straight, a badge formation, an
 * n-of-a-kind, or a lone 1 or 5 — or resolving one Balatro joker into a face.
 * Each move reports its point value and the dice left afterwards, and the two
 * recursions in `scoring.ts` share this so the rules are stated exactly once.
 *
 * The two joker faces differ here, and that difference is the whole reason the
 * generator is shaped this way:
 *
 *   Balatro       a free choice of face, so it is *resolved* into each face and
 *                 scored as that face from then on — including as a lone 1
 *   Devil's head  may only be spent inside a combination it completes, so it is
 *                 never resolved; `take` consumes it in place
 */

import type { ScoringRules, FormationValues } from "../data/badges.ts";
import { FACES, WILD_ALONE, WILD_COMBO } from "./counts.ts";
import type { CountVector } from "./counts.ts";

/** Everything the move generator needs beyond the roll itself. */
export interface ScoringConfig {
  readonly rules: ScoringRules;
  readonly formationValues: FormationValues;
}

/** One legal step: what it scores, and the dice remaining after it. */
export interface ScoringMove {
  readonly value: number;
  readonly rest: number[];
}

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

/**
 * Value of an n-of-a-kind under the active badge rules.
 *
 * @param face - Die face, 1-6.
 * @param n - Number of dice in the set.
 * @param config - Active rules and formation values.
 * @returns The point value, including the Emperor and Tyche multipliers.
 */
function combinationValue(face: number, n: number, config: ScoringConfig): number {
  const base = ofAKindValue(face, n);
  // Both badges name a specific three-die combination — "every 1+1+1" and
  // "three sixes" — so they multiply the triple only, not the four-, five- and
  // six-of-a-kind extensions of it. Applying the multiplier to those too made
  // the Emperor badge look like a 27,000-point swing in a game played to a few
  // thousand. The partition search still considers splitting six ones into two
  // tripled triples, so the better reading wins on its own merits.
  if (n === 3 && face === 1 && config.rules.emperorTriple) {
    return base * 3;
  }
  if (n === 3 && face === 6 && config.rules.tycheDouble) {
    return base * 2;
  }
  return base;
}

/**
 * Every legal single step from a position: take one combination (or resolve one
 * Balatro joker) and hand the leftovers back to the recursion.
 *
 * @param counts - Count vector of the remaining dice.
 * @param config - Active rules and formation values.
 * @returns Each move's point value and the dice left afterwards.
 */
export function scoringMoves(counts: CountVector, config: ScoringConfig): ScoringMove[] {
  const alone = counts[WILD_ALONE];
  if (alone > 0) {
    // A Balatro joker is a free choice of face — including a lone 1 — so it
    // can simply be resolved into each face and scored as that face from then
    // on. Resolving one at a time is sufficient: further jokers are handled by
    // the recursive call, and every assignment is reachable that way.
    const options: ScoringMove[] = [];
    for (let face = 0; face < FACES; face += 1) {
      const rest = counts.slice();
      rest[WILD_ALONE] = alone - 1;
      rest[face] += 1;
      options.push({ value: 0, rest });
    }
    return options;
  }

  const options: ScoringMove[] = [];
  const { rules, formationValues } = config;
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
        options.push({ value: combinationValue(face + 1, n, config), rest });
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
