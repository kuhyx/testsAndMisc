import { describe, expect, it } from 'vitest'
import type { Action, BettingState, SeatState } from './bettingRound'
import { legalActions } from './bettingRound'
import { chooseAction, decideAction, estimateEquity, potOddsToCall } from './opponentPolicy'
import { createRng } from './rng'
import type { Card } from './types'

const card = (rank: Card['rank'], suit: Card['suit']): Card => ({ rank, suit })

const seat = (overrides: Partial<SeatState> = {}): SeatState => ({
  stack: 100,
  committed: 0,
  hasActed: false,
  folded: false,
  allIn: false,
  ...overrides,
})

const betting = (overrides: Partial<BettingState> = {}): BettingState => ({
  street: 'preflop',
  pot: 0,
  toAct: 'player',
  seats: { player: seat(), opponent: seat() },
  betToCall: 0,
  minRaiseSize: 10,
  roundOver: false,
  ...overrides,
})

describe('chooseAction', () => {
  it('bets/raises the max size on strong equity when available', () => {
    const legal: Action[] = [{ type: 'fold' }, { type: 'check' }, { type: 'bet', amount: 10 }, { type: 'bet', amount: 100 }]
    expect(chooseAction(legal, 0.9, 0.2)).toEqual({ type: 'bet', amount: 100 })
  })

  it('bets/raises the min size on moderate equity when strong-equity threshold is not met', () => {
    const legal: Action[] = [{ type: 'fold' }, { type: 'check' }, { type: 'bet', amount: 10 }, { type: 'bet', amount: 100 }]
    expect(chooseAction(legal, 0.6, 0.2)).toEqual({ type: 'bet', amount: 10 })
  })

  it('calls/checks when equity clears pot odds but is below the aggressive thresholds', () => {
    const legal: Action[] = [{ type: 'fold' }, { type: 'call' }]
    expect(chooseAction(legal, 0.3, 0.2)).toEqual({ type: 'call' })
  })

  it('folds when equity is below pot odds and folding is available', () => {
    const legal: Action[] = [{ type: 'fold' }, { type: 'call' }]
    expect(chooseAction(legal, 0.1, 0.5)).toEqual({ type: 'fold' })
  })

  it('checks for free (no fold available, e.g. facing no bet) when equity is below thresholds', () => {
    const legal: Action[] = [{ type: 'check' }]
    expect(chooseAction(legal, 0.1, 0)).toEqual({ type: 'check' })
  })

  it('falls back to the only legal action when nothing else matches', () => {
    const legal: Action[] = [{ type: 'call' }]
    // High equity but no aggressive option and no fold available: falls through to passive.
    expect(chooseAction(legal, 0.95, 0.5)).toEqual({ type: 'call' })
  })

  it('picks the first legal action as a last resort when only aggressive options exist above threshold gating', () => {
    // Only a single bet is legal and equity/pot-odds are both very low with no fold/passive offered.
    const legal: Action[] = [{ type: 'bet', amount: 10 }]
    expect(chooseAction(legal, 0, 1)).toEqual({ type: 'bet', amount: 10 })
  })

  it('checks/calls when equity is low and there is no fold option available (facing an all-in check)', () => {
    // No fold offered (e.g. already all-in facing no further decision except check) — falls
    // through the "fold" branch to the passive one instead.
    const legal: Action[] = [{ type: 'check' }]
    expect(chooseAction(legal, 0, 1)).toEqual({ type: 'check' })
  })

  it('throws when given no legal actions at all', () => {
    expect(() => chooseAction([], 0.5, 0.5)).toThrow('no legal actions to choose from')
  })
})

describe('potOddsToCall', () => {
  it('is zero when nothing is owed', () => {
    expect(potOddsToCall(betting({ betToCall: 0 }))).toBe(0)
  })

  it('computes the fraction of the resulting pot the call would represent', () => {
    const s = betting({
      betToCall: 20,
      pot: 0,
      seats: { player: seat({ committed: 0 }), opponent: seat({ committed: 20 }) },
    })
    // toCall = 20, potAfterCall = 0 + 0 + 20 + 20 = 40, odds = 20/40 = 0.5
    expect(potOddsToCall(s)).toBe(0.5)
  })
})

describe('estimateEquity', () => {
  it('returns a value in [0, 1]', () => {
    const ownHole: [Card, Card] = [card(14, 'clubs'), card(14, 'diamonds')]
    const equity = estimateEquity(ownHole, [], createRng(1), 50)
    expect(equity).toBeGreaterThanOrEqual(0)
    expect(equity).toBeLessThanOrEqual(1)
  })

  it('is deterministic for a fixed seed', () => {
    const ownHole: [Card, Card] = [card(14, 'clubs'), card(14, 'diamonds')]
    const a = estimateEquity(ownHole, [], createRng(7), 30)
    const b = estimateEquity(ownHole, [], createRng(7), 30)
    expect(a).toBe(b)
  })

  it('returns 0 for zero iterations', () => {
    const ownHole: [Card, Card] = [card(2, 'clubs'), card(3, 'diamonds')]
    expect(estimateEquity(ownHole, [], createRng(1), 0)).toBe(0)
  })

  it('rates pocket aces higher than a weak hand on average, over many samples', () => {
    const strongHole: [Card, Card] = [card(14, 'clubs'), card(14, 'diamonds')]
    const weakHole: [Card, Card] = [card(2, 'hearts'), card(7, 'spades')]
    const strongEquity = estimateEquity(strongHole, [], createRng(3), 200)
    const weakEquity = estimateEquity(weakHole, [], createRng(3), 200)
    expect(strongEquity).toBeGreaterThan(weakEquity)
  })

  it('estimates equity with a partially dealt board (flop known)', () => {
    const ownHole: [Card, Card] = [card(14, 'clubs'), card(13, 'clubs')]
    const board: Card[] = [card(12, 'clubs'), card(11, 'clubs'), card(2, 'hearts')]
    const equity = estimateEquity(ownHole, board, createRng(5), 40)
    expect(equity).toBeGreaterThanOrEqual(0)
    expect(equity).toBeLessThanOrEqual(1)
  })
})

describe('decideAction', () => {
  it('always returns one of the offered legal actions', () => {
    const s = betting({ betToCall: 0, minRaiseSize: 10, seats: { player: seat({ stack: 100 }), opponent: seat() } })
    const legal = legalActions(s)
    const ownHole: [Card, Card] = [card(14, 'clubs'), card(14, 'diamonds')]
    const action = decideAction(s, legal, ownHole, [], createRng(1), 20)
    expect(legal).toContainEqual(action)
  })
})
