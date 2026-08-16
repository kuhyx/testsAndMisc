import { describe, expect, it } from 'vitest'
import { compareHandScore, evaluate7, rankLabel } from './handEval'
import type { HandScore } from './handEval'
import { card, seven } from '../test/handEvalFixtures'

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
