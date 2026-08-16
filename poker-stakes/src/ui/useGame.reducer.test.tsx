import { describe, expect, it } from 'vitest'
import { gameReducer, hasOutstandingDebt } from './useGame'
import type { GameState } from './useGame'
import { debt, initialState } from '../test/useGameFixtures'

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
