import { describe, expect, it } from 'vitest'
import { loadDebts, saveDebts } from './storage'
import type { SettledDebt } from './types'

const debt: SettledDebt = {
  id: 'd1',
  taskTypeId: 'pushups',
  owedUnits: 100,
  reason: 'cashOut',
  settledAt: 1,
  paidUnits: 0,
}

const makeStorage = (initial: Record<string, string> = {}): Storage => {
  const store = new Map(Object.entries(initial))
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

const throwingStorage = (): Storage => ({
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

describe('loadDebts', () => {
  it('returns an empty ok list when nothing is stored yet', () => {
    expect(loadDebts(makeStorage())).toEqual({ status: 'ok', debts: [] })
  })

  it('returns the stored debts when the shape is valid', () => {
    const storage = makeStorage({ 'poker-stakes:settledDebts': JSON.stringify([debt]) })
    expect(loadDebts(storage)).toEqual({ status: 'ok', debts: [debt] })
  })

  it('is unreadable when getItem throws (storage disabled/denied)', () => {
    expect(loadDebts(throwingStorage())).toEqual({ status: 'unreadable' })
  })

  it('is unreadable on malformed JSON', () => {
    const storage = makeStorage({ 'poker-stakes:settledDebts': '{not json' })
    expect(loadDebts(storage)).toEqual({ status: 'unreadable' })
  })

  it('is unreadable when the stored value is not an array', () => {
    const storage = makeStorage({ 'poker-stakes:settledDebts': JSON.stringify({ not: 'an array' }) })
    expect(loadDebts(storage)).toEqual({ status: 'unreadable' })
  })

  it('is unreadable when an array entry is missing required fields', () => {
    const storage = makeStorage({ 'poker-stakes:settledDebts': JSON.stringify([{ id: 'd1' }]) })
    expect(loadDebts(storage)).toEqual({ status: 'unreadable' })
  })

  // Each field's guard is asserted in ISOLATION — all other fields stay valid. The
  // missing-required-fields case above drops five fields at once, so it would still trip some
  // other check if any single guard were deleted, leaving that guard effectively untested.
  it.each([
    ['id', { id: 42 }],
    ['taskTypeId', { taskTypeId: null }],
    ['owedUnits', { owedUnits: 'ten' }],
    ['reason', { reason: 'quit' }],
    ['settledAt', { settledAt: '2026-01-01' }],
    ['paidUnits', { paidUnits: [] }],
  ])('is unreadable when only %s has the wrong type', (_field, override) => {
    const storage = makeStorage({ 'poker-stakes:settledDebts': JSON.stringify([{ ...debt, ...override }]) })
    expect(loadDebts(storage)).toEqual({ status: 'unreadable' })
  })

  it.each(['id', 'taskTypeId', 'owedUnits', 'reason', 'settledAt', 'paidUnits'])(
    'is unreadable when only %s is missing',
    (field) => {
      // Built by filtering rather than `delete`, which lint forbids on computed keys.
      const partial = Object.fromEntries(Object.entries(debt).filter(([key]) => key !== field))
      const storage = makeStorage({ 'poker-stakes:settledDebts': JSON.stringify([partial]) })
      expect(loadDebts(storage)).toEqual({ status: 'unreadable' })
    },
  )

  it('is unreadable when an array entry has an invalid reason value', () => {
    const bad = { ...debt, reason: 'quit' }
    const storage = makeStorage({ 'poker-stakes:settledDebts': JSON.stringify([bad]) })
    expect(loadDebts(storage)).toEqual({ status: 'unreadable' })
  })

  it('is unreadable when an array entry is null', () => {
    const storage = makeStorage({ 'poker-stakes:settledDebts': JSON.stringify([null]) })
    expect(loadDebts(storage)).toEqual({ status: 'unreadable' })
  })
})

describe('saveDebts', () => {
  it('round-trips through loadDebts', () => {
    const storage = makeStorage()
    saveDebts(storage, [debt])
    expect(loadDebts(storage)).toEqual({ status: 'ok', debts: [debt] })
  })
})
