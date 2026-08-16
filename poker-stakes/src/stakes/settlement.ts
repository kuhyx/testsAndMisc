import type { SessionOutcome } from '../engine/session'
import type { BuyIn, SettledDebt } from './types'

/**
 * Converts a finished session's outcome into a debt record. `owedUnits` scales inversely with
 * how well the player did: `2 × buyIn − finalChips`, floored at 0. Bust (finalChips === 0) needs
 * no special case — it's just this formula's natural output (2 × buyIn, the cap) for that input.
 */
export const settleSession = (buyIn: BuyIn, outcome: SessionOutcome, id: string, settledAt: number): SettledDebt => ({
  id,
  taskTypeId: buyIn.taskTypeId,
  owedUnits: Math.max(0, 2 * buyIn.chips - outcome.finalChips),
  reason: outcome.reason,
  settledAt,
  paidUnits: 0,
})
