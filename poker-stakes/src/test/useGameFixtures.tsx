import { StrictMode } from 'react'
import type { ReactElement, ReactNode } from 'react'
import type { SettledDebt } from '../stakes/types'
import type { GameState } from '../ui/useGame'

/**
 * Shared fixtures for the useGame test files.
 *
 * useGame.test.tsx was split by describe-block to stay under the 250-line cap;
 * these helpers are the part all three files need.
 */

export const debt = (overrides: Partial<SettledDebt> = {}): SettledDebt => ({
  id: 'd1',
  taskTypeId: 'pushups',
  owedUnits: 100,
  reason: 'cashOut',
  settledAt: 1,
  paidUnits: 0,
  ...overrides,
})

export const initialState: GameState = {
  debtLoad: { status: 'ok', debts: [] },
  buyIn: null,
  session: null,
  handPhase: null,
}

export const wrapper = ({ children }: { children: ReactNode }): ReactElement => <StrictMode>{children}</StrictMode>

/** An in-memory Storage stand-in, so tests never touch real localStorage. */
export const makeStorage = (): Storage => {
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

/** Storage that throws on every read/write, for the fail-closed paths. */
export const unreadableStorage = (): Storage => ({
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
