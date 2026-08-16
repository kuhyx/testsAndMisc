import { describe, expect, it } from 'vitest'
import { buildDeck } from './deck'
import { compareHandScore, rank5 } from './handEval'
import type { HandCategory } from './handEval'
import type { Card } from './types'
import { card, combinations5, five } from '../test/handEvalFixtures'

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
