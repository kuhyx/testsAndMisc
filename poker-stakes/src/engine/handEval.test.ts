import { describe, expect, it } from 'vitest'
import { buildDeck } from './deck'
import { compareHandScore, evaluate7, rank5, rankLabel } from './handEval'
import type { HandCategory, HandScore } from './handEval'
import type { Card } from './types'

const card = (rank: Card['rank'], suit: Card['suit']): Card => ({ rank, suit })

const five = (cards: readonly Card[]): [Card, Card, Card, Card, Card] => {
  if (cards.length !== 5) {
    throw new Error('five: expected exactly 5 cards')
  }
  const [a, b, c, d, e] = cards
  return [a, b, c, d, e] as [Card, Card, Card, Card, Card]
}

const seven = (cards: readonly Card[]): [Card, Card, Card, Card, Card, Card, Card] => {
  if (cards.length !== 7) {
    throw new Error('seven: expected exactly 7 cards')
  }
  const [a, b, c, d, e, f, g] = cards
  return [a, b, c, d, e, f, g] as [Card, Card, Card, Card, Card, Card, Card]
}

/** Generates all C(52,5) 5-card combinations from a 52-card deck as index tuples. */
function* combinations5(length: number): Generator<readonly [number, number, number, number, number]> {
  for (let a = 0; a < length; a += 1) {
    for (let b = a + 1; b < length; b += 1) {
      for (let c = b + 1; c < length; c += 1) {
        for (let d = c + 1; d < length; d += 1) {
          for (let e = d + 1; e < length; e += 1) {
            yield [a, b, c, d, e]
          }
        }
      }
    }
  }
}

describe('rank5 exhaustive classification', () => {
  it('classifies every 5-card hand out of 52 into the correct standard-count category', () => {
    const deck = buildDeck()
    const histogram: Record<HandCategory, number> = {
      highCard: 0,
      onePair: 0,
      twoPair: 0,
      trips: 0,
      straight: 0,
      flush: 0,
      fullHouse: 0,
      quads: 0,
      straightFlush: 0,
    }

    let total = 0
    for (const [i0, i1, i2, i3, i4] of combinations5(deck.length)) {
      const hand = five([deck[i0], deck[i1], deck[i2], deck[i3], deck[i4]] as Card[])
      const { category } = rank5(hand)
      histogram[category] += 1
      total += 1
    }

    expect(total).toBe(2_598_960)
    // Straight/flush counts here fold the royal flush into straightFlush (A-high straight flush).
    expect(histogram).toEqual({
      highCard: 1_302_540,
      onePair: 1_098_240,
      twoPair: 123_552,
      trips: 54_912,
      straight: 10_200,
      flush: 5_108,
      fullHouse: 3_744,
      quads: 624,
      straightFlush: 40,
    })
  }, 30_000)
})

describe('rank5 named fixtures', () => {
  it('scores a wheel straight (A-2-3-4-5) as 5-high', () => {
    const hand = five([
      card(14, 'clubs'),
      card(2, 'diamonds'),
      card(3, 'hearts'),
      card(4, 'spades'),
      card(5, 'clubs'),
    ])
    const score = rank5(hand)
    expect(score.category).toBe('straight')
    expect(score.tiebreakers).toEqual([5])
  })

  it('scores a wheel straight flush as 5-high straight flush', () => {
    const hand = five([
      card(14, 'clubs'),
      card(2, 'clubs'),
      card(3, 'clubs'),
      card(4, 'clubs'),
      card(5, 'clubs'),
    ])
    const score = rank5(hand)
    expect(score.category).toBe('straightFlush')
    expect(score.tiebreakers).toEqual([5])
  })

  it('scores a broadway (ace-high) straight correctly', () => {
    const hand = five([
      card(14, 'clubs'),
      card(13, 'diamonds'),
      card(12, 'hearts'),
      card(11, 'spades'),
      card(10, 'clubs'),
    ])
    const score = rank5(hand)
    expect(score.category).toBe('straight')
    expect(score.tiebreakers).toEqual([14])
  })

  it('breaks ties between two one-pair hands by kicker', () => {
    const a = rank5(
      five([card(9, 'clubs'), card(9, 'diamonds'), card(14, 'hearts'), card(4, 'spades'), card(2, 'clubs')]),
    )
    const b = rank5(
      five([card(9, 'clubs'), card(9, 'diamonds'), card(13, 'hearts'), card(4, 'spades'), card(2, 'clubs')]),
    )
    expect(compareHandScore(a, b)).toBe(1)
    expect(compareHandScore(b, a)).toBe(-1)
  })

  it('breaks ties between two full houses by trips rank, not pair rank', () => {
    // 2-2-2-A-A must beat 3-3-3-K-K: trips rank (2 < 3) decides, not the pair kicker (A > K).
    const twosOverAces = rank5(
      five([card(2, 'clubs'), card(2, 'diamonds'), card(2, 'hearts'), card(14, 'spades'), card(14, 'clubs')]),
    )
    const threesOverKings = rank5(
      five([card(3, 'clubs'), card(3, 'diamonds'), card(3, 'hearts'), card(13, 'spades'), card(13, 'clubs')]),
    )
    expect(compareHandScore(threesOverKings, twosOverAces)).toBe(1)
    expect(compareHandScore(twosOverAces, threesOverKings)).toBe(-1)
  })

  it('breaks ties between two two-pair hands by top pair, then bottom pair, then kicker', () => {
    const acesAndTwos = rank5(
      five([card(14, 'clubs'), card(14, 'diamonds'), card(2, 'hearts'), card(2, 'spades'), card(5, 'clubs')]),
    )
    const acesAndThrees = rank5(
      five([card(14, 'hearts'), card(14, 'spades'), card(3, 'clubs'), card(3, 'diamonds'), card(4, 'hearts')]),
    )
    expect(compareHandScore(acesAndThrees, acesAndTwos)).toBe(1)
    expect(compareHandScore(acesAndTwos, acesAndThrees)).toBe(-1)
  })

  it('breaks ties between two quads hands by the quad rank', () => {
    const fours = rank5(
      five([card(4, 'clubs'), card(4, 'diamonds'), card(4, 'hearts'), card(4, 'spades'), card(2, 'clubs')]),
    )
    const fives = rank5(
      five([card(5, 'clubs'), card(5, 'diamonds'), card(5, 'hearts'), card(5, 'spades'), card(2, 'diamonds')]),
    )
    expect(compareHandScore(fives, fours)).toBe(1)
    expect(compareHandScore(fours, fives)).toBe(-1)
  })

  it('breaks ties between two trips hands by trips rank then kickers', () => {
    const treys = rank5(
      five([card(3, 'clubs'), card(3, 'diamonds'), card(3, 'hearts'), card(14, 'spades'), card(13, 'clubs')]),
    )
    const fours = rank5(
      five([card(4, 'clubs'), card(4, 'diamonds'), card(4, 'hearts'), card(2, 'spades'), card(3, 'clubs')]),
    )
    expect(compareHandScore(fours, treys)).toBe(1)
    expect(compareHandScore(treys, fours)).toBe(-1)
  })

  it('breaks ties between two flushes by highest differing card', () => {
    const aceHighFlush = rank5(
      five([card(14, 'clubs'), card(9, 'clubs'), card(7, 'clubs'), card(4, 'clubs'), card(2, 'clubs')]),
    )
    const kingHighFlush = rank5(
      five([card(13, 'diamonds'), card(10, 'diamonds'), card(8, 'diamonds'), card(5, 'diamonds'), card(3, 'diamonds')]),
    )
    expect(compareHandScore(aceHighFlush, kingHighFlush)).toBe(1)
    expect(compareHandScore(kingHighFlush, aceHighFlush)).toBe(-1)
  })

  it('breaks ties between two straights by the high card', () => {
    const sevenHigh = rank5(
      five([card(7, 'clubs'), card(6, 'diamonds'), card(5, 'hearts'), card(4, 'spades'), card(3, 'clubs')]),
    )
    const eightHigh = rank5(
      five([card(8, 'clubs'), card(7, 'diamonds'), card(6, 'hearts'), card(5, 'spades'), card(4, 'clubs')]),
    )
    expect(compareHandScore(eightHigh, sevenHigh)).toBe(1)
    expect(compareHandScore(sevenHigh, eightHigh)).toBe(-1)
  })

  it('recognizes an exact split (identical hand scores)', () => {
    const a = rank5(
      five([card(9, 'clubs'), card(9, 'diamonds'), card(14, 'hearts'), card(4, 'spades'), card(2, 'clubs')]),
    )
    const b = rank5(
      five([card(9, 'hearts'), card(9, 'spades'), card(14, 'clubs'), card(4, 'diamonds'), card(2, 'hearts')]),
    )
    expect(compareHandScore(a, b)).toBe(0)
  })
})

describe('evaluate7', () => {
  it('picks the best 5 of 7 when the best hand uses only some hole+board cards', () => {
    const hand = seven([
      card(14, 'clubs'),
      card(14, 'diamonds'),
      card(14, 'hearts'),
      card(14, 'spades'),
      card(2, 'clubs'),
      card(3, 'diamonds'),
      card(4, 'hearts'),
    ])
    const score = evaluate7(hand)
    expect(score.category).toBe('quads')
  })

  it('matches the best rank5 result across all 21 combinations', () => {
    const cards = seven([
      card(10, 'clubs'),
      card(11, 'clubs'),
      card(12, 'clubs'),
      card(13, 'clubs'),
      card(14, 'clubs'),
      card(2, 'hearts'),
      card(2, 'diamonds'),
    ])
    const score = evaluate7(cards)
    expect(score.category).toBe('straightFlush')
    expect(score.tiebreakers).toEqual([14])
  })
})

describe('compareHandScore category comparison', () => {
  it('ranks a lower category below a higher one in both directions', () => {
    const high: HandScore = { category: 'quads', tiebreakers: [2] }
    const low: HandScore = { category: 'highCard', tiebreakers: [14] }
    expect(compareHandScore(high, low)).toBe(1)
    expect(compareHandScore(low, high)).toBe(-1)
  })
})

describe('compareHandScore tiebreaker padding', () => {
  it('treats a missing tiebreaker slot as lower than a present one', () => {
    const a: HandScore = { category: 'highCard', tiebreakers: [14, 10] }
    const b: HandScore = { category: 'highCard', tiebreakers: [14] }
    expect(compareHandScore(a, b)).toBe(1)
    expect(compareHandScore(b, a)).toBe(-1)
  })
})

describe('rankLabel', () => {
  it('labels face cards and ace', () => {
    expect(rankLabel(14)).toBe('A')
    expect(rankLabel(13)).toBe('K')
    expect(rankLabel(12)).toBe('Q')
    expect(rankLabel(11)).toBe('J')
  })

  it('labels number cards as their numeral', () => {
    expect(rankLabel(10)).toBe('10')
    expect(rankLabel(2)).toBe('2')
  })
})
