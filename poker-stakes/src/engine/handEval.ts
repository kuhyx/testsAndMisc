import type { Card, Rank } from './types'

export type HandCategory =
  | 'highCard'
  | 'onePair'
  | 'twoPair'
  | 'trips'
  | 'straight'
  | 'flush'
  | 'fullHouse'
  | 'quads'
  | 'straightFlush'

const CATEGORY_RANK: Record<HandCategory, number> = {
  highCard: 0,
  onePair: 1,
  twoPair: 2,
  trips: 3,
  straight: 4,
  flush: 5,
  fullHouse: 6,
  quads: 7,
  straightFlush: 8,
}

export interface HandScore {
  category: HandCategory
  tiebreakers: readonly number[]
}

type Five = readonly [Card, Card, Card, Card, Card]
type Seven = readonly [Card, Card, Card, Card, Card, Card, Card]

/** -1 if a < b, 0 if equal, 1 if a > b. Higher HandScore wins. */
export const compareHandScore = (a: HandScore, b: HandScore): -1 | 0 | 1 => {
  const catA = CATEGORY_RANK[a.category]
  const catB = CATEGORY_RANK[b.category]
  if (catA !== catB) {
    return catA > catB ? 1 : -1
  }
  const len = Math.max(a.tiebreakers.length, b.tiebreakers.length)
  for (let i = 0; i < len; i += 1) {
    const ta = a.tiebreakers[i] ?? 0
    const tb = b.tiebreakers[i] ?? 0
    if (ta !== tb) {
      return ta > tb ? 1 : -1
    }
  }
  return 0
}

const countBy = <T extends string | number>(values: readonly T[]): Map<T, number> => {
  const counts = new Map<T, number>()
  for (const value of values) {
    counts.set(value, (counts.get(value) ?? 0) + 1)
  }
  return counts
}

/** Ranks sorted descending, deduped, from a set of cards. */
const descendingRanks = (cards: Five): number[] => {
  const ranks = cards.map((c) => c.rank)
  return [...new Set(ranks)].sort((a, b) => b - a)
}

/** Straight high card, or null if the 5 ranks (deduped) don't form a run of 5. Wheel (A-2-3-4-5) scores as 5-high. */
const straightHigh = (uniqueDescRanks: readonly number[]): number | null => {
  if (uniqueDescRanks.length !== 5) {
    return null
  }
  const [r0, r1, r2, r3, r4] = uniqueDescRanks as readonly [number, number, number, number, number]
  const isRun = r0 - r1 === 1 && r1 - r2 === 1 && r2 - r3 === 1 && r3 - r4 === 1
  if (isRun) {
    return r0
  }
  const isWheel = r0 === 14 && r1 === 5 && r2 === 4 && r3 === 3 && r4 === 2
  return isWheel ? 5 : null
}

/** Evaluates exactly 5 cards. */
export const rank5 = (cards: Five): HandScore => {
  const suits = cards.map((c) => c.suit)
  const isFlush = new Set(suits).size === 1

  const rankCounts = countBy(cards.map((c) => c.rank))
  const uniqueDesc = descendingRanks(cards)
  const straightTop = straightHigh(uniqueDesc)

  const groups = [...rankCounts.entries()].sort((a, b) => {
    if (a[1] !== b[1]) {
      return b[1] - a[1]
    }
    return b[0] - a[0]
  })
  const groupCounts = groups.map(([, count]) => count)
  const groupRanks = groups.map(([rank]) => rank)

  if (isFlush && straightTop !== null) {
    return { category: 'straightFlush', tiebreakers: [straightTop] }
  }
  if (groupCounts[0] === 4) {
    return { category: 'quads', tiebreakers: groupRanks }
  }
  if (groupCounts[0] === 3 && groupCounts[1] === 2) {
    return { category: 'fullHouse', tiebreakers: groupRanks }
  }
  if (isFlush) {
    return { category: 'flush', tiebreakers: uniqueDesc }
  }
  if (straightTop !== null) {
    return { category: 'straight', tiebreakers: [straightTop] }
  }
  if (groupCounts[0] === 3) {
    return { category: 'trips', tiebreakers: groupRanks }
  }
  if (groupCounts[0] === 2 && groupCounts[1] === 2) {
    return { category: 'twoPair', tiebreakers: groupRanks }
  }
  if (groupCounts[0] === 2) {
    return { category: 'onePair', tiebreakers: groupRanks }
  }
  return { category: 'highCard', tiebreakers: uniqueDesc }
}

type FiveIndices = readonly [number, number, number, number, number]

/** All C(7,5) = 21 five-card index combinations out of positions 0-6, written as a literal tuple. */
const SEVEN_CHOOSE_FIVE: readonly [FiveIndices, ...FiveIndices[]] = [
  [0, 1, 2, 3, 4],
  [0, 1, 2, 3, 5],
  [0, 1, 2, 3, 6],
  [0, 1, 2, 4, 5],
  [0, 1, 2, 4, 6],
  [0, 1, 2, 5, 6],
  [0, 1, 3, 4, 5],
  [0, 1, 3, 4, 6],
  [0, 1, 3, 5, 6],
  [0, 1, 4, 5, 6],
  [0, 2, 3, 4, 5],
  [0, 2, 3, 4, 6],
  [0, 2, 3, 5, 6],
  [0, 2, 4, 5, 6],
  [0, 3, 4, 5, 6],
  [1, 2, 3, 4, 5],
  [1, 2, 3, 4, 6],
  [1, 2, 3, 5, 6],
  [1, 2, 4, 5, 6],
  [1, 3, 4, 5, 6],
  [2, 3, 4, 5, 6],
]

/** Best 5-card HandScore out of exactly 7 cards. */
export const evaluate7 = (cards: Seven): HandScore => {
  const [firstCombo, ...restCombos] = SEVEN_CHOOSE_FIVE
  const fiveFor = (combo: FiveIndices): Five =>
    [cards[combo[0]], cards[combo[1]], cards[combo[2]], cards[combo[3]], cards[combo[4]]] as Five

  let best = rank5(fiveFor(firstCombo))
  for (const combo of restCombos) {
    const score = rank5(fiveFor(combo))
    if (compareHandScore(score, best) > 0) {
      best = score
    }
  }
  return best
}

export const rankLabel = (rank: Rank): string => {
  if (rank === 14) {
    return 'A'
  }
  if (rank === 13) {
    return 'K'
  }
  if (rank === 12) {
    return 'Q'
  }
  if (rank === 11) {
    return 'J'
  }
  return String(rank)
}
