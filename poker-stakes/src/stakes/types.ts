import type { SessionEndReason } from '../engine/session'

export interface TaskType {
  id: string
  label: string
}

export interface BuyIn {
  taskTypeId: string
  chips: number
}

export interface SettledDebt {
  id: string
  taskTypeId: string
  owedUnits: number // 2×buyIn − finalChips, floored at 0
  reason: SessionEndReason // display-only; never branches settlement math
  settledAt: number
  paidUnits: number // partial progress; starts at 0, incremented via UI
}
