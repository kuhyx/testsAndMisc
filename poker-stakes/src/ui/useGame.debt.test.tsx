import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { hasOutstandingDebt, useGame } from './useGame'
import { makeStorage, wrapper } from '../test/useGameFixtures'

describe('useGame: debt settlement and persistence', () => {
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
