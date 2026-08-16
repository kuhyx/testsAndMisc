import { describe, expect, it } from 'vitest'
import type { SessionOutcome } from '../engine/session'
import { settleSession } from './settlement'
import type { BuyIn } from './types'

const buyIn: BuyIn = { taskTypeId: 'pushups', chips: 100 }

describe('settleSession', () => {
  const cases: { name: string; outcome: SessionOutcome; owedUnits: number }[] = [
    { name: 'doubled up', outcome: { reason: 'cashOut', finalChips: 200 }, owedUnits: 0 },
    { name: 'partial win', outcome: { reason: 'cashOut', finalChips: 150 }, owedUnits: 50 },
    { name: 'break-even', outcome: { reason: 'cashOut', finalChips: 100 }, owedUnits: 100 },
    { name: 'partial loss', outcome: { reason: 'cashOut', finalChips: 50 }, owedUnits: 150 },
    { name: 'bust to zero', outcome: { reason: 'bust', finalChips: 0 }, owedUnits: 200 },
  ]

  it.each(cases)('$name: owes $owedUnits units', ({ outcome, owedUnits }) => {
    const debt = settleSession(buyIn, outcome, 'debt-1', 12345)
    expect(debt.owedUnits).toBe(owedUnits)
  })

  it('carries the task type, reason, id, and settledAt through unchanged', () => {
    const outcome: SessionOutcome = { reason: 'bust', finalChips: 0 }
    const debt = settleSession(buyIn, outcome, 'debt-42', 999)
    expect(debt).toEqual({
      id: 'debt-42',
      taskTypeId: 'pushups',
      owedUnits: 200,
      reason: 'bust',
      settledAt: 999,
      paidUnits: 0,
    })
  })
})
