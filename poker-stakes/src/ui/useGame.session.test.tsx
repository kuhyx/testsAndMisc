import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { hasOutstandingDebt, useGame } from './useGame'
import { makeStorage, unreadableStorage, wrapper } from '../test/useGameFixtures'

describe('useGame', () => {
  it('starts with no debt and no session, blocked=false', () => {
    const { result } = renderHook(() => useGame(makeStorage(), 1), { wrapper })
    expect(hasOutstandingDebt(result.current.state.debtLoad)).toBe(false)
    expect(result.current.state.session).toBeNull()
  })

  it('starts blocked when storage is unreadable, fail-closed', () => {
    const { result } = renderHook(() => useGame(unreadableStorage(), 1), { wrapper })
    expect(result.current.state.debtLoad).toEqual({ status: 'unreadable' })
    expect(hasOutstandingDebt(result.current.state.debtLoad)).toBe(true)
  })

  it('buyIn is a no-op when storage is unreadable — the hard gate itself blocks, not just the UI', () => {
    // Regression: an earlier version derived the gate's debt list via a helper that collapsed
    // `{status: 'unreadable'}` to `[]`, which made `hasOutstandingDebt` see an empty (non-blocking)
    // list and let a session start despite fail-closed storage. The hook's `buyIn` must itself
    // refuse, not rely on a UI component to have already checked `state.debtLoad`.
    const { result } = renderHook(() => useGame(unreadableStorage(), 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 200 })
    })
    expect(result.current.state.session).toBeNull()
  })

  it('buy-in starts a session and pauses on the player seat (StrictMode double-invoke safe)', () => {
    const { result } = renderHook(() => useGame(makeStorage(), 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 200 })
    })
    expect(result.current.state.session).not.toBeNull()
    expect(result.current.state.session?.handsPlayed).toBe(0)
    expect(result.current.state.handPhase?.kind).toBe('awaiting')
    // If StrictMode's double-invoke perturbed the generator, stacks would already be inconsistent.
    const stacks = result.current.state.session?.stacks
    expect(stacks?.player).toBeGreaterThan(0)
    expect(stacks?.opponent).toBeGreaterThan(0)
  })

  it('buyIn is a no-op while a debt is outstanding (hard gate, not just BuyInScreen UI)', () => {
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 200 })
    })
    // Cash out immediately: `cashOut` requires `betweenHands`, but hand 1 just started as
    // `awaiting`. Fold to reach `betweenHands` deterministically without depending on a specific
    // showdown outcome.
    act(() => {
      result.current.submitPlayerAction({ type: 'fold' })
    })
    expect(result.current.state.handPhase?.kind).toBe('betweenHands')
    act(() => {
      result.current.cashOut()
    })
    expect(result.current.state.session).toBeNull()
    const debtsBefore = result.current.state.debtLoad.status === 'ok' ? result.current.state.debtLoad.debts : []
    expect(debtsBefore).toHaveLength(1)

    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 50 })
    })
    expect(result.current.state.session).toBeNull()
    const debtsAfter = result.current.state.debtLoad.status === 'ok' ? result.current.state.debtLoad.debts : []
    expect(debtsAfter).toHaveLength(1)
  })

  it('buyIn rejects a non-positive or fractional chip count (chips are integers throughout)', () => {
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 0 })
    })
    expect(result.current.state.session).toBeNull()
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: -5 })
    })
    expect(result.current.state.session).toBeNull()
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 2.5 })
    })
    expect(result.current.state.session).toBeNull()
  })

  it('submitting a second action right after a hand resolves into betweenHands does not throw', () => {
    // Regression: handRef used to only be cleared on settle, not on the betweenHands path, so a
    // late/duplicate submitPlayerAction call after a hand resolved without ending the session hit
    // `hand.submit()` on an already-complete InteractiveHand and threw out of the event handler.
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 200 })
    })
    act(() => {
      result.current.submitPlayerAction({ type: 'fold' })
    })
    expect(result.current.state.handPhase?.kind).toBe('betweenHands')
    expect(() => {
      act(() => {
        result.current.submitPlayerAction({ type: 'fold' })
      })
    }).not.toThrow()
    // Still safely between hands — the stale submit was a no-op, not a state corruption.
    expect(result.current.state.handPhase?.kind).toBe('betweenHands')
  })

  it('cashOut is a no-op when no session is live', () => {
    const { result } = renderHook(() => useGame(makeStorage(), 1), { wrapper })
    act(() => {
      result.current.cashOut()
    })
    expect(result.current.state.session).toBeNull()
    expect(result.current.state.debtLoad).toEqual({ status: 'ok', debts: [] })
  })

  it('cashOut is a no-op mid-hand (only legal between hands, per the settlement-exploit fix)', () => {
    // Buying in leaves a live hand `awaiting` a player decision. Cashing out here must be a
    // no-op: `session.stacks` predates this hand's blinds/bets, so settling against it would let
    // a player see the deal, cash out at the pre-hand stack, and have posted chips vanish.
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 200 })
    })
    expect(result.current.state.handPhase?.kind).toBe('awaiting')
    act(() => {
      result.current.cashOut()
    })
    expect(result.current.state.session).not.toBeNull()
    expect(result.current.state.debtLoad).toEqual({ status: 'ok', debts: [] })
  })

  it('a hand that reaches showdown lands in betweenHands, not auto-dealing the next one', () => {
    // Seed 1 at a 200-chip buy-in, always checking/calling: 4 submits carry the first hand to
    // showdown. The session must land in `betweenHands` (handsPlayed incremented, no live hand)
    // rather than silently starting hand 2 — that pause is what makes cashOut safe.
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 200 })
    })
    for (let i = 0; i < 4; i += 1) {
      const phase = result.current.state.handPhase
      if (phase?.kind !== 'awaiting') {
        break
      }
      const { betting } = phase.step
      const toCall = betting.betToCall - betting.seats.player.committed
      act(() => {
        result.current.submitPlayerAction(toCall > 0 ? { type: 'call' } : { type: 'check' })
      })
    }
    expect(result.current.state.session?.handsPlayed).toBe(1)
    expect(result.current.state.session?.outcome).toBeNull()
    const phase = result.current.state.handPhase
    expect(phase).toMatchObject({ kind: 'betweenHands' })
    expect(phase?.kind === 'betweenHands' ? phase.lastResult : undefined).not.toBeNull()
  })

  it('dealHand starts the next hand after betweenHands', () => {
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 200 })
    })
    act(() => {
      result.current.submitPlayerAction({ type: 'fold' })
    })
    expect(result.current.state.handPhase?.kind).toBe('betweenHands')
    act(() => {
      result.current.dealHand()
    })
    expect(result.current.state.handPhase?.kind).toBe('awaiting')
    expect(result.current.state.session?.handsPlayed).toBe(1)
  })

  it('dealHand is a no-op before any buy-in', () => {
    const { result } = renderHook(() => useGame(makeStorage(), 1), { wrapper })
    act(() => {
      result.current.dealHand()
    })
    expect(result.current.state.session).toBeNull()
    expect(result.current.state.handPhase).toBeNull()
  })

  it('submitPlayerAction is a no-op before any buy-in (no live hand to advance)', () => {
    const { result } = renderHook(() => useGame(makeStorage(), 1), { wrapper })
    act(() => {
      result.current.submitPlayerAction({ type: 'fold' })
    })
    expect(result.current.state.session).toBeNull()
    expect(result.current.state.handPhase).toBeNull()
  })

  it('a zero-player-decision hand (all-in from the blind post) settles instead of soft-locking', () => {
    // Buy-in of 1 chip: deriveBlindSize floors BB at 2, SB at 1 — the button posts their entire
    // 1-chip stack as the small blind, an immediate all-in with zero player decision points.
    // `dealHand` must fold that hand's result into the session and settle rather than leaving a
    // live, un-settled session with no pending decision (the soft-lock this session's advisor
    // review caught: `initialBettingState` used to reset `allIn: false` on every street).
    // Seed 1 deterministically busts the player on this exact first hand.
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 1 })
    })
    expect(result.current.state.session).toBeNull()
    expect(result.current.state.handPhase).toBeNull()
    const debts = result.current.state.debtLoad.status === 'ok' ? result.current.state.debtLoad.debts : []
    expect(debts).toHaveLength(1)
    expect(debts[0]).toMatchObject({ owedUnits: 2, reason: 'bust' })
  })

})
