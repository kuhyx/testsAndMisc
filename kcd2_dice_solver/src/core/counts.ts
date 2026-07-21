/**
 * Packed representation of a roll.
 *
 * A roll is only ever needed as a *multiset* of faces, so it is stored as seven
 * counts — faces 1-6 plus the wildcard slot — and those seven counts are packed
 * into one integer. That packing is the reason the solver is fast: adding a die
 * to a category is a single integer addition, and the scorer's memo can be keyed
 * on the packed value directly, so a warm run never touches an array at all.
 */

/** Number of die faces. */
export const FACES = 6;

/** Length of a count vector: six faces plus the wildcard slot. */
export const CATEGORIES = 7;

/** Index of the wildcard ("substitute") slot in a count vector. */
export const WILD = 6;

/**
 * Base used for packing. Base 8 holds up to 7 dice in any one category, which is
 * the most a hand can ever have: six dice plus the one a Might badge adds.
 */
export const RADIX = 8;

/**
 * A roll expressed as counts per category: indices 0-5 are faces 1-6 and index
 * 6 is the number of wildcard dice.
 */
export type CountVector = readonly number[];

/** How much a packed key changes when one die joins a category. */
export const SLOT_STEP: readonly number[] = Array.from(
  { length: CATEGORIES },
  (_, slot) => RADIX ** (CATEGORIES - 1 - slot),
);

/**
 * Pack a count vector into an integer key.
 *
 * @param counts - Count vector to encode.
 * @returns A non-negative integer uniquely identifying the vector.
 */
export function encode(counts: CountVector): number {
  let key = 0;
  for (const count of counts) {
    key = key * RADIX + count;
  }
  return key;
}

/**
 * Unpack an integer key back into a count vector.
 *
 * @param key - Key produced by {@link encode} or by summing {@link SLOT_STEP}.
 * @returns The seven-element count vector it stands for.
 */
export function decode(key: number): number[] {
  const counts = new Array<number>(CATEGORIES).fill(0);
  let rest = key;
  for (let i = CATEGORIES - 1; i >= 0; i -= 1) {
    counts[i] = rest % RADIX;
    rest = Math.floor(rest / RADIX);
  }
  return counts;
}
