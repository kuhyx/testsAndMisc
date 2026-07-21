/**
 * Small fuzzy matcher for picking dice and badges by name.
 *
 * Written here rather than pulled in as a dependency: it is short, it needs to
 * be covered by the project's 100% bar anyway, and the ranking rules are
 * specific to this list ("wei" should find "Weighted die", "paintb" should find
 * "Painter's die B").
 *
 * It finds the *best* alignment rather than the leftmost one. A greedy
 * left-to-right scan is a few lines shorter, but it binds the "d" of a query
 * like "die" to the "d" that ends "Weighted", which both under-scores the right
 * answer and underlines the wrong letters.
 */

export interface FuzzyMatch<T> {
  readonly item: T;
  readonly score: number;
  /** Indices in the haystack that the query matched, for highlighting. */
  readonly indices: readonly number[];
}

/** A scored alignment of the query onto the haystack. */
interface Alignment {
  readonly score: number;
  readonly indices: readonly number[];
}

/** Points for matching a character at all. */
const MATCH_BONUS = 1;
/** Extra points when a character continues an unbroken run. */
const ADJACENCY_BONUS = 4;
/** Extra points when a character starts a word. */
const BOUNDARY_BONUS = 3;
/** Per-character penalty, so a short name outranks a long one that also matches. */
const LENGTH_PENALTY = 0.01;

/**
 * Whether the character at `index` begins a word.
 *
 * @param target - The lower-cased haystack.
 * @param index - Position to test.
 * @returns True when the previous character is not alphanumeric.
 */
function isWordStart(target: string, index: number): boolean {
  if (index === 0) {
    return true;
  }
  return !/[a-z0-9]/.test(target[index - 1]);
}

/**
 * Match a query against a string as a subsequence, taking the best alignment.
 *
 * Scoring rewards, in order: matching at all, matching consecutively, and
 * matching at a word boundary. A shorter haystack breaks ties, so an exact short
 * name beats a long name that merely contains the letters.
 *
 * @param query - What the user typed; case-insensitive, spaces are ignored.
 * @param haystack - The string being searched.
 * @returns The best alignment with its score and matched indices, or null.
 */
export function fuzzyMatch(query: string, haystack: string): Alignment | null {
  const needle = query.toLowerCase().replace(/\s+/g, "");
  const target = haystack.toLowerCase();
  if (needle.length === 0) {
    return { score: 0, indices: [] };
  }

  // best[i][k] = the best alignment of needle[i..] given needle[i] sits at k.
  // Filled from the end of the needle backwards so each entry only depends on
  // entries already computed.
  const memo = new Map<number, Alignment | null>();

  const solve = (i: number, at: number): Alignment | null => {
    const key = i * target.length + at;
    const cached = memo.get(key);
    if (cached !== undefined) {
      return cached;
    }

    const own = MATCH_BONUS + (isWordStart(target, at) ? BOUNDARY_BONUS : 0);
    let result: Alignment | null = null;

    if (i === needle.length - 1) {
      result = { score: own, indices: [at] };
    } else {
      for (let next = at + 1; next < target.length; next += 1) {
        if (target[next] !== needle[i + 1]) {
          continue;
        }
        const tail = solve(i + 1, next);
        if (!tail) {
          continue;
        }
        const adjacency = next === at + 1 ? ADJACENCY_BONUS : 0;
        const score = own + adjacency + tail.score;
        if (!result || score > result.score) {
          result = { score, indices: [at, ...tail.indices] };
        }
      }
    }

    memo.set(key, result);
    return result;
  };

  let best: Alignment | null = null;
  for (let start = 0; start < target.length; start += 1) {
    if (target[start] !== needle[0]) {
      continue;
    }
    const candidate = solve(0, start);
    if (candidate && (!best || candidate.score > best.score)) {
      best = candidate;
    }
  }

  if (!best) {
    return null;
  }
  return { score: best.score - target.length * LENGTH_PENALTY, indices: best.indices };
}

/**
 * Filter and rank a list by fuzzy name match.
 *
 * @param query - What the user typed. An empty query keeps the original order.
 * @param items - The items to search.
 * @param key - Extracts the searchable string from an item.
 * @returns Matching items, best first.
 */
export function fuzzyFilter<T>(
  query: string,
  items: readonly T[],
  key: (item: T) => string,
): FuzzyMatch<T>[] {
  const matches: FuzzyMatch<T>[] = [];
  for (const item of items) {
    const match = fuzzyMatch(query, key(item));
    if (match) {
      matches.push({ item, score: match.score, indices: match.indices });
    }
  }
  if (query.trim().length === 0) {
    return matches;
  }
  return matches.sort((a, b) => b.score - a.score);
}
