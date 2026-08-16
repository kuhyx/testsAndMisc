import type { Rng } from './rng'
import { nextInt } from './rng'
import type { Card, Rank, Suit } from './types'

const SUITS: readonly Suit[] = ['clubs', 'diamonds', 'hearts', 'spades']
const RANKS: readonly Rank[] = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]

/** Builds a deterministic 52-card deck in fixed suit/rank order. */
export const buildDeck = (): readonly Card[] => {
  const deck: Card[] = []
  for (const suit of SUITS) {
    for (const rank of RANKS) {
      deck.push({ rank, suit })
    }
  }
  return deck
}

/**
 * Selection-sampling shuffle: repeatedly pulls a random remaining card into
 * the output. Uses splice (never indexed reads) so no element access is ever
 * typed `Card | undefined` under noUncheckedIndexedAccess.
 */
export const shuffleDeck = (rng: Rng, deck: readonly Card[]): Card[] => {
  const pool: Card[] = [...deck]
  const out: Card[] = []
  while (pool.length > 0) {
    for (const card of pool.splice(nextInt(rng, pool.length), 1)) {
      out.push(card)
    }
  }
  return out
}

export interface DealCursor {
  deck: readonly Card[]
  next: number
}

export const createDealCursor = (deck: readonly Card[]): DealCursor => ({ deck, next: 0 })

/** Deals `count` cards from the cursor, returning the cards and an advanced cursor. */
export const dealCards = (
  cursor: DealCursor,
  count: number,
): { cards: Card[]; cursor: DealCursor } => {
  if (cursor.next + count > cursor.deck.length) {
    throw new Error('dealCards: not enough cards remaining in deck')
  }
  const cards = cursor.deck.slice(cursor.next, cursor.next + count)
  return { cards, cursor: { deck: cursor.deck, next: cursor.next + count } }
}
