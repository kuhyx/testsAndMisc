import { describe, expect, it } from 'vitest'
import type { Action, BettingState } from './bettingRound'
import { legalActions } from './bettingRound'
import { createRng } from './rng'
import { cashOutSession, deriveBlindSize, playSessionHand, startSession } from './session'
import type { Seat } from './types'

const enforceLegal = (
  decide: (betting: BettingState, seat: Seat) => Action,
): ((betting: BettingState, seat: Seat) => Action) => {
  return (betting, seat) => {
    const action = decide(betting, seat)
    expect(legalActions(betting)).toContainEqual(action)
    return action
  }
}

const alwaysCheckOrCall = enforceLegal((betting) => {
  const toCall = betting.betToCall - betting.seats[betting.toAct].committed
  return toCall > 0 ? { type: 'call' } : { type: 'check' }
})

/** Shoves all-in whenever a bet/raise is legal for the given seat, otherwise checks/calls. */
const shoveForSeat = (targetSeat: Seat): ((betting: BettingState, seat: Seat) => Action) =>
  enforceLegal((betting, seat) => {
    if (seat !== targetSeat) {
      return alwaysCheckOrCall(betting, seat)
    }
    const actions = legalActions(betting)
    const shove = actions.find((a) => a.type === 'bet' || a.type === 'raise')
    return shove ?? alwaysCheckOrCall(betting, seat)
  })

describe('deriveBlindSize', () => {
  it('floors a tiny buy-in to the minimum viable blinds (BB=2, SB=1)', () => {
    expect(deriveBlindSize(20)).toEqual({ bigBlind: 2, smallBlind: 1 })
  })

  it('scales blinds proportionally for a large buy-in', () => {
    expect(deriveBlindSize(1000)).toEqual({ bigBlind: 10, smallBlind: 5 })
  })

  it('never produces a small blind equal to the big blind', () => {
    for (const buyIn of [1, 2, 20, 99, 100, 250, 10_000]) {
      const { bigBlind, smallBlind } = deriveBlindSize(buyIn)
      expect(smallBlind).toBeLessThan(bigBlind)
      expect(smallBlind).toBeGreaterThanOrEqual(1)
    }
  })
})

describe('startSession', () => {
  it('starts both stacks equal to the buy-in with the player on the button', () => {
    const session = startSession({ buyInChips: 100 })
    expect(session.stacks).toEqual({ player: 100, opponent: 100 })
    expect(session.buttonSeat).toBe('player')
    expect(session.handsPlayed).toBe(0)
    expect(session.outcome).toBeNull()
  })
})

describe('playSessionHand', () => {
  it('updates stacks, increments handsPlayed, and rotates the button', () => {
    const session = startSession({ buyInChips: 200 })
    const { session: next } = playSessionHand(session, createRng(1), 200, { decide: alwaysCheckOrCall })
    expect(next.handsPlayed).toBe(1)
    expect(next.buttonSeat).toBe('opponent')
    expect(next.stacks.player + next.stacks.opponent).toBe(400)
  })

  it('throws when called on an already-ended session', () => {
    const session = startSession({ buyInChips: 200 })
    const ended = cashOutSession(session)
    expect(() => playSessionHand(ended, createRng(1), 200, { decide: alwaysCheckOrCall })).toThrow(
      'session has already ended',
    )
  })

  it('records a bust outcome when the player stack hits zero (deterministic seed)', () => {
    // Seed 1: player always shoves all-in, opponent always checks/calls — player loses and busts.
    const session = startSession({ buyInChips: 10 })
    const { session: after } = playSessionHand(session, createRng(1), 10, { decide: shoveForSeat('player') })
    expect(after.outcome).toEqual({ reason: 'bust', finalChips: 0 })
    expect(after.stacks.player).toBe(0)
  })

  it('records a cash-out-equivalent outcome when the opponent stack hits zero (deterministic seed)', () => {
    // Seed 100: opponent always shoves all-in, player always checks/calls — opponent loses and busts.
    const session = startSession({ buyInChips: 10 })
    const { session: after } = playSessionHand(session, createRng(100), 10, { decide: shoveForSeat('opponent') })
    expect(after.stacks.opponent).toBe(0)
    expect(after.outcome).toEqual({ reason: 'cashOut', finalChips: after.stacks.player })
    expect(after.stacks.player).toBeGreaterThan(0)
  })

  it('conserves total chips across many hands until the session ends', () => {
    let session = startSession({ buyInChips: 100 })
    let seed = 1
    while (session.outcome === null && session.handsPlayed < 30) {
      const result = playSessionHand(session, createRng(seed), 100, { decide: alwaysCheckOrCall })
      session = result.session
      seed += 1
      expect(session.stacks.player + session.stacks.opponent).toBe(200)
    }
  })
})

describe('cashOutSession', () => {
  it('records the current player stack as the outcome', () => {
    const session = startSession({ buyInChips: 100 })
    const { session: afterHand } = playSessionHand(session, createRng(1), 100, { decide: alwaysCheckOrCall })
    const cashedOut = cashOutSession(afterHand)
    expect(cashedOut.outcome).toEqual({ reason: 'cashOut', finalChips: afterHand.stacks.player })
  })

  it('throws when called on an already-ended session', () => {
    const session = startSession({ buyInChips: 100 })
    const cashedOut = cashOutSession(session)
    expect(() => cashOutSession(cashedOut)).toThrow('session has already ended')
  })
})
