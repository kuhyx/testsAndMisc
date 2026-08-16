import { act, renderHook } from '@testing-library/react'
import { StrictMode } from 'react'
import type { ReactElement, ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import type { SettledDebt } from '../stakes/types'
import { gameReducer, hasOutstandingDebt, useGame } from './useGame'
import type { GameState } from './useGame'

const debt = (overrides: Partial<SettledDebt> = {}): SettledDebt => ({
  id: 'd1',
  taskTypeId: 'pushups',
  owedUnits: 100,
  reason: 'cashOut',
  settledAt: 1,
  paidUnits: 0,
  ...overrides,
})

const initialState: GameState = {
  debtLoad: { status: 'ok', debts: [] },
  buyIn: null,
  session: null,
  handPhase: null,
}

describe('hasOutstandingDebt', () => {
  it('blocks when storage was unreadable', () => {
    expect(hasOutstandingDebt({ status: 'unreadable' })).toBe(true)
  })

  it('does not block an empty debt list', () => {
    expect(hasOutstandingDebt({ status: 'ok', debts: [] })).toBe(false)
  })

  it('does not block a fully paid debt', () => {
    expect(hasOutstandingDebt({ status: 'ok', debts: [debt({ owedUnits: 50, paidUnits: 50 })] })).toBe(false)
  })

  it('does not block a debt that owes zero units (doubled-up cash-out)', () => {
    expect(hasOutstandingDebt({ status: 'ok', debts: [debt({ owedUnits: 0, paidUnits: 0 })] })).toBe(false)
  })

  it('blocks a partially paid debt', () => {
    expect(hasOutstandingDebt({ status: 'ok', debts: [debt({ owedUnits: 100, paidUnits: 40 })] })).toBe(true)
  })
})

describe('gameReducer', () => {
  it('buyIn sets buyIn/session and clears handPhase', () => {
    const session: GameState['session'] = {
      stacks: { player: 100, opponent: 100 },
      buttonSeat: 'player',
      handsPlayed: 0,
      outcome: null,
    }
    const next = gameReducer(initialState, {
      type: 'buyIn',
      buyIn: { taskTypeId: 'pushups', chips: 100 },
      session,
    })
    expect(next).toEqual({
      debtLoad: { status: 'ok', debts: [] },
      buyIn: { taskTypeId: 'pushups', chips: 100 },
      session,
      handPhase: null,
    })
  })

  it('debtSettled clears the live session and resets to the buy-in gate', () => {
    const mid: GameState = {
      ...initialState,
      buyIn: { taskTypeId: 'pushups', chips: 100 },
      session: {
        stacks: { player: 0, opponent: 200 },
        buttonSeat: 'player',
        handsPlayed: 3,
        outcome: { reason: 'bust', finalChips: 0 },
      },
      handPhase: { kind: 'betweenHands', lastResult: null },
    }
    const settled = [debt({ owedUnits: 200 })]
    const next = gameReducer(mid, { type: 'debtSettled', debts: settled })
    expect(next).toEqual({
      debtLoad: { status: 'ok', debts: settled },
      buyIn: null,
      session: null,
      handPhase: null,
    })
  })

  it('debtProgressLogged updates debtLoad only', () => {
    const next = gameReducer(initialState, { type: 'debtProgressLogged', debts: [debt({ paidUnits: 20 })] })
    expect(next.debtLoad).toEqual({ status: 'ok', debts: [debt({ paidUnits: 20 })] })
  })
})

const wrapper = ({ children }: { children: ReactNode }): ReactElement => <StrictMode>{children}</StrictMode>

const makeStorage = (): Storage => {
  const store = new Map<string, string>()
  return {
    getItem: (key: string): string | null => store.get(key) ?? null,
    setItem: (key: string, value: string): void => {
      store.set(key, value)
    },
    removeItem: (key: string): void => {
      store.delete(key)
    },
    clear: (): void => {
      store.clear()
    },
    key: (): null => null,
    get length(): number {
      return store.size
    },
  }
}

const unreadableStorage = (): Storage => ({
  getItem: (): never => {
    throw new Error('denied')
  },
  setItem: (): never => {
    throw new Error('denied')
  },
  removeItem: (): undefined => undefined,
  clear: (): undefined => undefined,
  key: (): null => null,
  length: 0,
})

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

  it('a zero-player-decision hand that the all-in player survives lands in betweenHands, not settled', () => {
    // Seed 1, 4-chip buy-in, always folding when a decision exists: by hand 3 (handsPlayed=2) the
    // player is down to 1 chip and posts it as the small blind — all-in, zero decision points.
    // The all-in player wins/ties that hand and ends above 0, so the session must survive into
    // `betweenHands` rather than settling — the sibling branch to the bust case above.
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 4 })
    })
    let guard = 0
    while (result.current.state.session !== null && result.current.state.session.handsPlayed < 3 && guard < 10) {
      const phase = result.current.state.handPhase
      if (phase?.kind === 'betweenHands') {
        act(() => {
          result.current.dealHand()
        })
      } else if (phase?.kind === 'awaiting') {
        act(() => {
          result.current.submitPlayerAction({ type: 'fold' })
        })
      } else {
        break
      }
      guard += 1
    }
    expect(guard).toBeLessThan(10)
    expect(result.current.state.session).not.toBeNull()
    expect(result.current.state.session?.handsPlayed).toBe(3)
    expect(result.current.state.handPhase?.kind).toBe('betweenHands')
    expect(result.current.state.session?.stacks.player).toBeGreaterThan(0)
  })

  it('logDebtProgress with an unknown debt id leaves the debt list unchanged', () => {
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 200 })
    })
    act(() => {
      result.current.submitPlayerAction({ type: 'fold' })
    })
    act(() => {
      result.current.cashOut()
    })
    const before = result.current.state.debtLoad.status === 'ok' ? result.current.state.debtLoad.debts : []
    act(() => {
      result.current.logDebtProgress('no-such-id', 10)
    })
    const after = result.current.state.debtLoad.status === 'ok' ? result.current.state.debtLoad.debts : []
    expect(after).toEqual(before)
  })

  it('cashing out between hands (never played a hand to showdown) settles a debt equal to the full buy-in', () => {
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
      result.current.cashOut()
    })
    expect(result.current.state.session).toBeNull()
    expect(result.current.state.debtLoad.status).toBe('ok')
    const debts = result.current.state.debtLoad.status === 'ok' ? result.current.state.debtLoad.debts : []
    expect(debts).toHaveLength(1)
    expect(debts[0]?.reason).toBe('cashOut')
  })

  it('an unpaid debt persists to storage and blocks a subsequent load', () => {
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 200 })
    })
    act(() => {
      result.current.submitPlayerAction({ type: 'fold' })
    })
    act(() => {
      result.current.cashOut()
    })
    const { result: second } = renderHook(() => useGame(storage, 2), { wrapper })
    expect(hasOutstandingDebt(second.current.state.debtLoad)).toBe(true)
  })

  it('logDebtProgress clamps paidUnits to owedUnits and persists', () => {
    const storage = makeStorage()
    const { result } = renderHook(() => useGame(storage, 1), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 200 })
    })
    act(() => {
      result.current.submitPlayerAction({ type: 'fold' })
    })
    act(() => {
      result.current.cashOut()
    })
    const debtId = result.current.state.debtLoad.status === 'ok' ? result.current.state.debtLoad.debts[0]?.id : undefined
    if (debtId === undefined) {
      throw new Error('expected a settled debt')
    }
    act(() => {
      result.current.logDebtProgress(debtId, 500)
    })
    const debts = result.current.state.debtLoad.status === 'ok' ? result.current.state.debtLoad.debts : []
    expect(debts[0]?.paidUnits).toBe(debts[0]?.owedUnits)

    const { result: reloaded } = renderHook(() => useGame(storage, 3), { wrapper })
    expect(hasOutstandingDebt(reloaded.current.state.debtLoad)).toBe(false)
  })

  it('bust ends the session with a debt of exactly 2×buyIn', () => {
    const storage = makeStorage()
    // Seed 4 at a 20-chip buy-in, always checking/calling as the player, deterministically busts
    // the player within a handful of hands (found by probing seeds 1-10; every other seed either
    // busts with the same owedUnits=40 result or ends in the opponent-bust/cashOut branch covered
    // above). Deals explicitly via dealHand() between hands, matching the new no-auto-continue API.
    const { result } = renderHook(() => useGame(storage, 4), { wrapper })
    act(() => {
      result.current.buyIn({ taskTypeId: 'pushups', chips: 20 })
    })
    let guard = 0
    while (result.current.state.session !== null && guard < 20) {
      const phase = result.current.state.handPhase
      if (phase?.kind === 'betweenHands') {
        act(() => {
          result.current.dealHand()
        })
      } else if (phase?.kind === 'awaiting') {
        const { betting } = phase.step
        const toCall = betting.betToCall - betting.seats.player.committed
        act(() => {
          result.current.submitPlayerAction(toCall > 0 ? { type: 'call' } : { type: 'check' })
        })
      } else {
        break
      }
      guard += 1
    }
    expect(guard).toBeLessThan(20)
    expect(result.current.state.session).toBeNull()
    const debts = result.current.state.debtLoad.status === 'ok' ? result.current.state.debtLoad.debts : []
    expect(debts).toHaveLength(1)
    expect(debts[0]).toMatchObject({ owedUnits: 40, reason: 'bust' })
  })
})
