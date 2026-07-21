/**
 * Seeded pseudo-random number generator (mulberry32).
 *
 * `Math.random` is deliberately not used anywhere in this project: the Monte
 * Carlo turn simulator and the search's random restarts both need to be
 * reproducible so their tests can assert exact numbers instead of tolerances.
 */

/** A function returning the next value in [0, 1). */
export type Random = () => number;

/**
 * Create a deterministic random source.
 *
 * @param seed - Any 32-bit integer; the same seed always yields the same stream.
 * @returns A function producing successive values in [0, 1).
 */
export function mulberry32(seed: number): Random {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Pick a random integer in `[0, bound)`.
 *
 * @param random - Source of randomness.
 * @param bound - Exclusive upper bound, must be positive.
 * @returns An integer in the half-open range.
 */
export function randomInt(random: Random, bound: number): number {
  return Math.floor(random() * bound);
}
