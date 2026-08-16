import { describe, expect, it } from 'vitest'
import { applyAction, legalActions } from './bettingRound'
import type { BettingState, SeatState } from './bettingRound'

const seat = (overrides: Partial<SeatState> = {}): SeatState => ({
  stack: 100,
  committed: 0,
  hasActed: false,
  folded: false,
  allIn: false,
  ...overrides,
})

const state = (overrides: Partial<BettingState> = {}): BettingState => ({
  street: 'preflop',
  pot: 0,
  toAct: 'player',
  seats: { player: seat(), opponent: seat() },
  betToCall: 0,
  minRaiseSize: 10,
  roundOver: false,
  ...overrides,
})

const totalChips = (s: BettingState): number =>
  s.pot + s.seats.player.stack + s.seats.player.committed + s.seats.opponent.stack + s.seats.opponent.committed

describe('legalActions', () => {
  it('returns no actions once the round is over', () => {
    expect(legalActions(state({ roundOver: true }))).toEqual([])
  })

  it('returns no actions for a folded actor', () => {
    expect(legalActions(state({ seats: { player: seat({ folded: true }), opponent: seat() } }))).toEqual([])
  })

  it('returns no actions for an all-in actor', () => {
    expect(
      legalActions(state({ seats: { player: seat({ allIn: true, stack: 0 }), opponent: seat() } })),
    ).toEqual([])
  })

  it('offers check (not call) when nothing is owed', () => {
    const actions = legalActions(state({ betToCall: 0 }))
    expect(actions).toContainEqual({ type: 'fold' })
    expect(actions).toContainEqual({ type: 'check' })
    expect(actions.some((a) => a.type === 'call')).toBe(false)
  })

  it('offers call (not check) when a bet is owed', () => {
    const actions = legalActions(
      state({ betToCall: 20, seats: { player: seat({ committed: 0 }), opponent: seat({ committed: 20 }) } }),
    )
    expect(actions).toContainEqual({ type: 'fold' })
    expect(actions).toContainEqual({ type: 'call' })
    expect(actions.some((a) => a.type === 'check')).toBe(false)
  })

  it('offers bet (not raise) as the open-action name when nothing is committed yet', () => {
    const actions = legalActions(state({ betToCall: 0 }))
    expect(actions.some((a) => a.type === 'bet')).toBe(true)
    expect(actions.some((a) => a.type === 'raise')).toBe(false)
  })

  it('offers raise (not bet) as the open-action name when a bet is already in', () => {
    const actions = legalActions(
      state({ betToCall: 20, seats: { player: seat({ committed: 0 }), opponent: seat({ committed: 20 }) } }),
    )
    expect(actions.some((a) => a.type === 'raise')).toBe(true)
    expect(actions.some((a) => a.type === 'bet')).toBe(false)
  })

  it('offers a single bet/raise size (all-in only) when stack is too small for a full min-raise', () => {
    const actions = legalActions(
      state({
        betToCall: 20,
        minRaiseSize: 50,
        seats: { player: seat({ committed: 0, stack: 25 }), opponent: seat({ committed: 20 }) },
      }),
    )
    const raises = actions.filter((a) => a.type === 'raise')
    expect(raises).toHaveLength(1)
    expect(raises[0]).toEqual({ type: 'raise', amount: 25 })
  })

  it('offers no bet/raise when the actor can only call all-in (stack equals amount owed)', () => {
    const actions = legalActions(
      state({
        betToCall: 20,
        seats: { player: seat({ committed: 0, stack: 20 }), opponent: seat({ committed: 20 }) },
      }),
    )
    expect(actions.some((a) => a.type === 'bet' || a.type === 'raise')).toBe(false)
    expect(actions).toContainEqual({ type: 'call' })
  })

  it('offers both a minimum and an all-in size when stack exceeds the minimum raise', () => {
    const actions = legalActions(state({ betToCall: 0, minRaiseSize: 10, seats: { player: seat({ stack: 100 }), opponent: seat() } }))
    const bets = actions.filter((a) => a.type === 'bet')
    expect(bets).toHaveLength(2)
    expect(bets[0]).toEqual({ type: 'bet', amount: 10 })
    expect(bets[1]).toEqual({ type: 'bet', amount: 100 })
  })
})

describe('applyAction: fold', () => {
  it('marks the actor folded and ends the round', () => {
    const s = state()
    const next = applyAction(s, { type: 'fold' })
    expect(next.seats.player.folded).toBe(true)
    expect(next.roundOver).toBe(true)
    expect(totalChips(next)).toBe(totalChips(s))
  })
})

describe('applyAction: check', () => {
  it('passes action to the other seat without ending the round if they have not acted', () => {
    const s = state()
    const next = applyAction(s, { type: 'check' })
    expect(next.toAct).toBe('opponent')
    expect(next.roundOver).toBe(false)
  })

  it('ends the round when both seats have checked', () => {
    const s = state()
    const afterPlayer = applyAction(s, { type: 'check' })
    const afterOpponent = applyAction(afterPlayer, { type: 'check' })
    expect(afterOpponent.roundOver).toBe(true)
    expect(totalChips(afterOpponent)).toBe(totalChips(s))
  })
})

describe('applyAction: call', () => {
  it('matches the bet, ends the round, and preserves total chips (opponent already acted)', () => {
    const s = state({
      betToCall: 20,
      toAct: 'player',
      seats: {
        player: seat({ committed: 0, stack: 100 }),
        opponent: seat({ committed: 20, stack: 80, hasActed: true }),
      },
    })
    const next = applyAction(s, { type: 'call' })
    expect(next.seats.player.committed).toBe(20)
    expect(next.seats.player.stack).toBe(80)
    expect(next.roundOver).toBe(true)
    expect(totalChips(next)).toBe(totalChips(s))
  })

  it('does NOT end the round when the other seat has not yet acted (heads-up big-blind option)', () => {
    // SB completes preflop to match the BB's posted blind; BB has not acted this round yet.
    const s = state({
      betToCall: 10,
      toAct: 'player',
      seats: {
        player: seat({ committed: 0, stack: 100 }),
        opponent: seat({ committed: 10, stack: 90, hasActed: false }),
      },
    })
    const next = applyAction(s, { type: 'call' })
    expect(next.roundOver).toBe(false)
    expect(next.toAct).toBe('opponent')
    expect(totalChips(next)).toBe(totalChips(s))
  })

  it('goes all-in when the stack is smaller than the call amount owed is not offered, but a call for exactly the stack works', () => {
    const s = state({
      betToCall: 20,
      seats: { player: seat({ committed: 0, stack: 20 }), opponent: seat({ committed: 20 }) },
    })
    const next = applyAction(s, { type: 'call' })
    expect(next.seats.player.stack).toBe(0)
    expect(next.seats.player.allIn).toBe(true)
    expect(totalChips(next)).toBe(totalChips(s))
  })
})

describe('applyAction: bet/raise', () => {
  it('opens a bet, updates betToCall and minRaiseSize, and requires the other seat to act again', () => {
    const s = state({ minRaiseSize: 10 })
    const next = applyAction(s, { type: 'bet', amount: 10 })
    expect(next.betToCall).toBe(10)
    expect(next.minRaiseSize).toBe(10)
    expect(next.toAct).toBe('opponent')
    expect(next.roundOver).toBe(false)
    expect(next.seats.opponent.hasActed).toBe(false)
    expect(totalChips(next)).toBe(totalChips(s))
  })

  // A short all-in (a raise that adds LESS than the current minimum) must not lower the floor for
  // whoever acts next — that is what `Math.max(state.minRaiseSize, raiseSize)` protects. Without
  // the floor, a 5-chip all-in over a min-raise of 50 would let the next player re-raise by 5.
  it('does not lower minRaiseSize when an all-in raise is smaller than the current minimum', () => {
    const s = state({
      betToCall: 20,
      minRaiseSize: 50,
      toAct: 'opponent',
      seats: {
        player: seat({ committed: 20, stack: 80, hasActed: true }),
        opponent: seat({ committed: 0, stack: 25 }),
      },
    })
    // All-in for 25 total: only 5 more than the 20 to call, well under the 50 min-raise.
    const next = applyAction(s, { type: 'raise', amount: 25 })
    expect(next.betToCall).toBe(25)
    expect(next.minRaiseSize).toBe(50)
    expect(next.seats.opponent.allIn).toBe(true)
    expect(totalChips(next)).toBe(totalChips(s))
  })

  it('raises on top of an existing bet and tracks the new min-raise size', () => {
    const s = state({
      betToCall: 10,
      minRaiseSize: 10,
      toAct: 'opponent',
      seats: { player: seat({ committed: 10, stack: 90, hasActed: true }), opponent: seat({ committed: 0, stack: 100 }) },
    })
    const next = applyAction(s, { type: 'raise', amount: 30 })
    expect(next.betToCall).toBe(30)
    expect(next.minRaiseSize).toBe(20)
    expect(next.toAct).toBe('player')
    expect(totalChips(next)).toBe(totalChips(s))
  })

  it('caps spend at the actor stack and marks all-in when betting the full stack', () => {
    const s = state({ seats: { player: seat({ stack: 40 }), opponent: seat() } })
    const next = applyAction(s, { type: 'bet', amount: 40 })
    expect(next.seats.player.stack).toBe(0)
    expect(next.seats.player.allIn).toBe(true)
    expect(totalChips(next)).toBe(totalChips(s))
  })
})

describe('a full betting round preserves total chips end to end', () => {
  it('bet, raise, call sequence', () => {
    let s = state({ minRaiseSize: 10, seats: { player: seat({ stack: 200 }), opponent: seat({ stack: 200 }) } })
    const initialTotal = totalChips(s)
    s = applyAction(s, { type: 'bet', amount: 20 })
    s = applyAction(s, { type: 'raise', amount: 60 })
    s = applyAction(s, { type: 'call' })
    expect(s.roundOver).toBe(true)
    expect(totalChips(s)).toBe(initialTotal)
  })
})
