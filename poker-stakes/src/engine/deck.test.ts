import { describe, expect, it } from 'vitest'
import { buildDeck, createDealCursor, dealCards, shuffleDeck } from './deck'
import { createRng } from './rng'
import type { Card } from './types'

const cardKey = (card: Card): string => `${String(card.rank)}-${card.suit}`

describe('buildDeck', () => {
  it('builds exactly 52 unique cards', () => {
    const deck = buildDeck()
    expect(deck).toHaveLength(52)
    expect(new Set(deck.map(cardKey)).size).toBe(52)
  })
})

describe('shuffleDeck', () => {
  it('returns a permutation of the input deck', () => {
    const deck = buildDeck()
    const shuffled = shuffleDeck(createRng(1), deck)
    expect(shuffled).toHaveLength(52)
    expect(new Set(shuffled.map(cardKey))).toEqual(new Set(deck.map(cardKey)))
  })

  it('is deterministic for a given seed', () => {
    const deck = buildDeck()
    const a = shuffleDeck(createRng(42), deck)
    const b = shuffleDeck(createRng(42), deck)
    expect(a).toEqual(b)
  })

  it('produces a different order for a different seed', () => {
    const deck = buildDeck()
    const a = shuffleDeck(createRng(1), deck)
    const b = shuffleDeck(createRng(2), deck)
    expect(a).not.toEqual(b)
  })

  it('does not mutate the input deck', () => {
    const deck = buildDeck()
    const before = [...deck]
    shuffleDeck(createRng(7), deck)
    expect(deck).toEqual(before)
  })
})

describe('dealCards', () => {
  it('deals the requested count and advances the cursor', () => {
    const deck = shuffleDeck(createRng(3), buildDeck())
    const cursor0 = createDealCursor(deck)
    const { cards, cursor: cursor1 } = dealCards(cursor0, 2)
    expect(cards).toEqual(deck.slice(0, 2))
    expect(cursor1.next).toBe(2)
  })

  it('deals sequential batches without overlap', () => {
    const deck = shuffleDeck(createRng(4), buildDeck())
    const { cursor: afterHole } = dealCards(createDealCursor(deck), 4)
    const { cards: flop, cursor: afterFlop } = dealCards(afterHole, 3)
    expect(flop).toEqual(deck.slice(4, 7))
    expect(afterFlop.next).toBe(7)
  })

  it('throws when asked for more cards than remain', () => {
    const deck = buildDeck()
    const cursor = createDealCursor(deck)
    expect(() => dealCards(cursor, 53)).toThrow('not enough cards remaining')
  })
})
