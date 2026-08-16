import { describe, expect, it } from 'vitest'
import type { Action, BettingState } from './bettingRound'
import { legalActions } from './bettingRound'
import { playHand } from './handFlow'
import type { HandSetup } from './handFlow'
import { createRng } from './rng'
import type { Seat } from './types'

const setup = (overrides: Partial<HandSetup> = {}): HandSetup => ({
  buttonSeat: 'player',
  bigBlind: 10,
  smallBlind: 5,
  stacks: { player: 200, opponent: 200 },
  ...overrides,
})

const totalStack = (setupArg: HandSetup): number => setupArg.stacks.player + setupArg.stacks.opponent

/** Wraps a decide() callback, asserting the returned action is always one legalActions offered. */
const enforceLegal = (
  decide: (betting: BettingState, seat: Seat) => Action,
): ((betting: BettingState, seat: Seat) => Action) => {
  return (betting, seat) => {
    const action = decide(betting, seat)
    expect(legalActions(betting)).toContainEqual(action)
    return action
  }
}

/** Builds a decide() callback from a fixed queue of actions, applied in call order regardless of seat. */
const scripted = (actions: readonly Action[]): ((betting: BettingState, seat: Seat) => Action) => {
  const queue = [...actions]
  return enforceLegal(() => {
    const next = queue.shift()
    if (next === undefined) {
      throw new Error('scripted: ran out of scripted actions')
    }
    return next
  })
}

/** Always checks/calls — used to run a hand to showdown with minimal betting. */
const alwaysCheckOrCall = enforceLegal((betting) => {
  const toCall = betting.betToCall - betting.seats[betting.toAct].committed
  return toCall > 0 ? { type: 'call' } : { type: 'check' }
})

describe('playHand: showdown', () => {
  it('runs a full hand to showdown and awards the pot to the better hand', () => {
    const s = setup()
    const result = playHand(createRng(1), s, { decide: alwaysCheckOrCall })
    expect(result.wentToShowdown).toBe(true)
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
    expect(['player', 'opponent', 'split']).toContain(result.winner)
  })

  it('is deterministic for a fixed seed', () => {
    const s = setup()
    const a = playHand(createRng(99), s, { decide: alwaysCheckOrCall })
    const b = playHand(createRng(99), s, { decide: alwaysCheckOrCall })
    expect(a).toEqual(b)
  })
})

describe('playHand: fold preflop', () => {
  it('awards the pot to the non-folder and refunds nothing beyond the folded blind', () => {
    const s = setup()
    const decide = scripted([{ type: 'fold' }])
    const result = playHand(createRng(2), s, { decide })
    expect(result.wentToShowdown).toBe(false)
    expect(result.loserSeat).toBe('player')
    expect(result.winner).toBe('opponent')
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
  })
})

describe('playHand: fold postflop', () => {
  it('carries the pot across streets and awards it on a later fold', () => {
    const s = setup()
    // Preflop: player calls, opponent checks (round ends). Flop: opponent bets, player folds.
    const decide = scripted([{ type: 'call' }, { type: 'check' }, { type: 'bet', amount: 10 }, { type: 'fold' }])
    const result = playHand(createRng(3), s, { decide })
    expect(result.wentToShowdown).toBe(false)
    expect(result.loserSeat).toBe('player')
    expect(result.potAwarded).toBeGreaterThanOrEqual(s.bigBlind * 2)
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
  })
})

describe('playHand: early all-in preserves total chips', () => {
  /** Shoves all-in whenever a bet/raise is legal, otherwise calls/checks — drives every hand to an all-in quickly. */
  const shoveOrCheckCall = enforceLegal((betting, seat) => {
    const actions = legalActions(betting)
    const shove = actions.find((a) => a.type === 'bet' || a.type === 'raise')
    if (shove !== undefined) {
      return shove
    }
    return alwaysCheckOrCall(betting, seat)
  })

  it('handles a short-stacked all-in preflop and resolves at showdown', () => {
    const s = setup({ stacks: { player: 15, opponent: 200 } })
    const result = playHand(createRng(4), s, { decide: shoveOrCheckCall })
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
    expect(result.wentToShowdown).toBe(true)
  })
})

describe('playHand: fold — opponent as loser', () => {
  it('awards the pot to the player when the opponent folds', () => {
    const s = setup()
    // Preflop: player calls, opponent gets the option and folds.
    const decide = scripted([{ type: 'call' }, { type: 'fold' }])
    const result = playHand(createRng(6), s, { decide })
    expect(result.loserSeat).toBe('opponent')
    expect(result.winner).toBe('player')
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
  })
})

describe('playHand: uncalled excess is returned in both directions', () => {
  it('returns excess to the opponent when the opponent bets more and the player folds', () => {
    const s = setup()
    // Preflop: call, check. Flop: opponent bets, player folds — opponent's committed ends up
    // higher than player's, exercising the "opponent higher" branch of returnUncalledExcess.
    const decide = scripted([{ type: 'call' }, { type: 'check' }, { type: 'bet', amount: 10 }, { type: 'fold' }])
    const result = playHand(createRng(3), s, { decide })
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
  })

  it('returns excess to the player when the player bets more and the opponent folds', () => {
    const s = setup()
    // Preflop: call, check. Flop: opponent checks first, player bets, opponent folds — player's
    // committed ends up higher, exercising the "player higher" branch of returnUncalledExcess.
    const decide = scripted([{ type: 'call' }, { type: 'check' }, { type: 'check' }, { type: 'bet', amount: 10 }, { type: 'fold' }])
    const result = playHand(createRng(3), s, { decide })
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
  })
})

describe('playHand: split pot', () => {
  it('splits the pot evenly on an exact tie (deterministic seed)', () => {
    // Seed 15 with check/call-only play produces a genuine board-play tie at showdown.
    const s = setup()
    const result = playHand(createRng(15), s, { decide: alwaysCheckOrCall })
    expect(result.winner).toBe('split')
    expect(result.potAwarded % 2).toBe(0)
    expect(result.finalStacks).toEqual({ player: 200, opponent: 200 })
  })

  it('conserves total chips across many seeds regardless of outcome', () => {
    const s = setup()
    for (let seed = 1; seed <= 50; seed += 1) {
      const result = playHand(createRng(seed), s, { decide: alwaysCheckOrCall })
      expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
      expect(result.potAwarded % 2).toBe(0)
    }
  })
})

describe('playHand: button rotation', () => {
  it('lets the opponent be the button/small blind and act first preflop', () => {
    const s = setup({ buttonSeat: 'opponent' })
    const result = playHand(createRng(5), s, { decide: alwaysCheckOrCall })
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
  })
})

describe('playHand: a seat all-in from a blind post never acts again', () => {
  it('never offers a decision to a 0-stack seat on a later street (button posts SB all-in)', () => {
    // Button posts smallBlind=1 from a 1-chip stack, going all-in preflop. A fresh, buggy
    // `allIn: false` reset on flop/turn/river would let this 0-stack seat fold/check again.
    const s = setup({ buttonSeat: 'player', bigBlind: 2, smallBlind: 1, stacks: { player: 1, opponent: 200 } })
    const seenActingWithZeroStack: Seat[] = []
    const decide = (betting: BettingState, seat: Seat): Action => {
      if (betting.seats[seat].stack === 0) {
        seenActingWithZeroStack.push(seat)
      }
      return alwaysCheckOrCall(betting, seat)
    }
    const result = playHand(createRng(1), s, { decide })
    expect(seenActingWithZeroStack).toEqual([])
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
  })

  it('never offers a decision to a 0-stack seat on a later street (non-button posts BB all-in)', () => {
    const s = setup({ buttonSeat: 'player', bigBlind: 2, smallBlind: 1, stacks: { player: 200, opponent: 2 } })
    const seenActingWithZeroStack: Seat[] = []
    const decide = (betting: BettingState, seat: Seat): Action => {
      if (betting.seats[seat].stack === 0) {
        seenActingWithZeroStack.push(seat)
      }
      return alwaysCheckOrCall(betting, seat)
    }
    const result = playHand(createRng(1), s, { decide })
    expect(seenActingWithZeroStack).toEqual([])
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
  })
})
