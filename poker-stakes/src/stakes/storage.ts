import type { SettledDebt } from './types'

/** Exported so tests can seed a scripted ledger without duplicating the key string. */
export const DEBTS_STORAGE_KEY = 'poker-stakes:settledDebts'

export type DebtLoad = { status: 'ok'; debts: SettledDebt[] } | { status: 'unreadable' }

const isSettledDebt = (value: unknown): value is SettledDebt => {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const v = value as Record<string, unknown>
  return (
    typeof v.id === 'string' &&
    typeof v.taskTypeId === 'string' &&
    typeof v.owedUnits === 'number' &&
    (v.reason === 'cashOut' || v.reason === 'bust') &&
    typeof v.settledAt === 'number' &&
    typeof v.paidUnits === 'number'
  )
}

/** Fail-closed: any read/parse/shape error yields 'unreadable', never a silently-empty list. */
export const loadDebts = (storage: Storage): DebtLoad => {
  let raw: string | null
  try {
    raw = storage.getItem(DEBTS_STORAGE_KEY)
  } catch {
    return { status: 'unreadable' }
  }
  if (raw === null) {
    return { status: 'ok', debts: [] }
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    return { status: 'unreadable' }
  }
  if (!Array.isArray(parsed) || !parsed.every(isSettledDebt)) {
    return { status: 'unreadable' }
  }
  return { status: 'ok', debts: parsed }
}

export const saveDebts = (storage: Storage, debts: SettledDebt[]): void => {
  storage.setItem(DEBTS_STORAGE_KEY, JSON.stringify(debts))
}
