import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import { DEBTS_STORAGE_KEY } from './stakes/storage'
import type { SettledDebt } from './stakes/types'
import { App } from './App'

/** In-memory Storage so each test gets an isolated ledger, never the real localStorage. */
const memoryStorage = (seed: Record<string, string> = {}): Storage => {
  const map = new Map<string, string>(Object.entries(seed))
  return {
    get length(): number {
      return map.size
    },
    clear: (): void => {
      map.clear()
    },
    getItem: (key: string): string | null => map.get(key) ?? null,
    key: (index: number): string | null => [...map.keys()][index] ?? null,
    removeItem: (key: string): void => {
      map.delete(key)
    },
    setItem: (key: string, value: string): void => {
      map.set(key, value)
    },
  }
}

const debt = (overrides: Partial<SettledDebt> = {}): SettledDebt => ({
  id: 'd1',
  taskTypeId: 'pushups',
  owedUnits: 100,
  reason: 'cashOut',
  settledAt: 1,
  paidUnits: 0,
  ...overrides,
})

const storageWithDebts = (debts: SettledDebt[]): Storage =>
  memoryStorage({ [DEBTS_STORAGE_KEY]: JSON.stringify(debts) })

/** BuyInScreen's pre-filled chip count — the value every test below sits down with. */
const DEFAULT_BUY_IN = 100

/** The betting controls, or null between hands / before any session exists. */
const bettingControls = (): HTMLElement | null => document.querySelector<HTMLElement>('.controls')

/** The first legal action currently offered, or null if no decision is pending. */
const firstLegalAction = (): HTMLElement | null => {
  const controls = bettingControls()
  if (controls === null) {
    return null
  }
  return within(controls).getAllByRole('button')[0] ?? null
}

/** Plays hands until the session ends, always taking the first legal action offered. */
const playUntilSettled = async (user: ReturnType<typeof userEvent.setup>, maxActions = 400): Promise<void> => {
  for (let i = 0; i < maxActions; i += 1) {
    const deal = screen.queryByText('Deal next hand')
    if (deal !== null) {
      await user.click(deal)
      continue
    }
    const action = firstLegalAction()
    if (action === null) {
      return
    }
    await user.click(action)
  }
}

describe('App', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders the title and the buy-in screen before any session starts', () => {
    render(<App storage={memoryStorage()} seed={1} />)
    expect(screen.getByText('Poker Stakes')).toBeInTheDocument()
    expect(screen.getByText('Sit down')).toBeInTheDocument()
    expect(screen.getByText('No debts settled yet.')).toBeInTheDocument()
  })

  it('defaults to the real localStorage and a clock-derived seed when no props are given', () => {
    render(<App />)
    expect(screen.getByText('Poker Stakes')).toBeInTheDocument()
    expect(screen.getByText('Sit down')).toBeInTheDocument()
  })

  it('buys in and deals the opening hand straight away', async () => {
    const user = userEvent.setup()
    render(<App storage={memoryStorage()} seed={7} />)
    await user.click(screen.getByText('Sit down'))
    expect(screen.queryByText('Sit down')).not.toBeInTheDocument()
    // Sitting down deals the opening hand immediately, so the player faces a decision at once.
    expect(bettingControls()).not.toBeNull()
  })

  it('records a debt in the history panel once the session settles', async () => {
    const user = userEvent.setup()
    render(<App storage={memoryStorage()} seed={7} />)
    await user.click(screen.getByText('Sit down'))
    await playUntilSettled(user)
    // Settling returns to the buy-in screen; the debt is now in the durable ledger. It appears
    // twice — once in the buy-in gate, once in the history panel — which is the intended layout.
    expect(screen.queryByText('No debts settled yet.')).not.toBeInTheDocument()
    expect(screen.getAllByText(/Pushups: /).length).toBeGreaterThan(0)
  })

  it('blocks a new buy-in while a debt is outstanding, and unblocks once it is logged off', async () => {
    const user = userEvent.setup()
    render(<App storage={storageWithDebts([debt({ owedUnits: 10, paidUnits: 0 })])} seed={7} />)
    expect(screen.queryByText('Sit down')).not.toBeInTheDocument()
    expect(screen.getByText(/outstanding debt/)).toBeInTheDocument()

    // The gate and the history panel each render a control for the same debt; either clears it.
    const [gateInput] = screen.getAllByLabelText('Log units done for Pushups')
    const [logButton] = screen.getAllByText('Log progress')
    if (gateInput === undefined || logButton === undefined) {
      throw new Error('expected the outstanding-debt controls to render')
    }
    await user.type(gateInput, '10')
    await user.click(logButton)

    expect(screen.getByText('Sit down')).toBeInTheDocument()
  })

  it('blocks buying in when the stored ledger is unreadable (fail-closed)', () => {
    render(<App storage={memoryStorage({ [DEBTS_STORAGE_KEY]: 'not json' })} seed={7} />)
    expect(screen.queryByText('Sit down')).not.toBeInTheDocument()
    // Both surfaces fail closed independently: the buy-in gate and the history panel.
    expect(
      screen.getByText('Your debt history could not be read. Buying in is blocked until this is resolved.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Your debt history could not be read.')).toBeInTheDocument()
  })

  it('cashes out between hands and settles the resulting debt', async () => {
    const user = userEvent.setup()
    render(<App storage={memoryStorage()} seed={7} />)
    await user.click(screen.getByText('Sit down'))

    // Play the opening hand to completion so we land in `betweenHands`, where cash-out is legal.
    for (let i = 0; i < 200 && screen.queryByText('Deal next hand') === null; i += 1) {
      const action = firstLegalAction()
      if (action === null) {
        break
      }
      await user.click(action)
    }

    // Pin the actual numbers: the panel previews `2*buyIn - stack`, and the settled ledger row
    // must show exactly that same figure. A looser assertion here would pass whether or not a
    // debt was recorded at all.
    const preview = screen.getByText(/Current stack: \d+ chips\./)
    const previewText = preview.textContent
    const parsed = /Current stack: (\d+) chips\. Cashing out now would owe (\d+) units\./.exec(previewText)
    if (parsed === null) {
      throw new Error(`cash-out panel did not match the expected copy: ${previewText}`)
    }
    const [, stackText, owedText] = parsed
    const finalChips = Number(stackText)
    const previewOwed = Number(owedText)
    expect(previewOwed).toBe(Math.max(0, 2 * DEFAULT_BUY_IN - finalChips))

    await user.click(screen.getByText('Leave table'))

    // Cashing out settles the session, so the app returns to the (now debt-gated) buy-in screen,
    // and the ledger row carries the same owed figure the preview promised.
    expect(screen.getByText(/outstanding debt/)).toBeInTheDocument()
    expect(screen.getAllByText(`Pushups: 0 / ${String(previewOwed)} done`).length).toBeGreaterThan(0)
  })

  it('settles a bust at exactly twice the buy-in', async () => {
    const user = userEvent.setup()
    const storage = memoryStorage()
    render(<App storage={storage} seed={7} />)
    await user.click(screen.getByText('Sit down'))
    await playUntilSettled(user)

    const stored: unknown = JSON.parse(storage.getItem(DEBTS_STORAGE_KEY) ?? '[]')
    expect(Array.isArray(stored)).toBe(true)
    const debts = stored as SettledDebt[]
    expect(debts.length).toBeGreaterThan(0)
    const settled = debts[debts.length - 1]
    if (settled === undefined) {
      throw new Error('expected a settled debt')
    }
    // Seed 7 + always-take-the-first-legal-action busts deterministically, so this pins the
    // bust case exactly rather than accepting either branch. Busting to zero is the formula's
    // natural maximum, not a special case: 2*buyIn - 0.
    expect(settled.reason).toBe('bust')
    expect(settled.owedUnits).toBe(2 * DEFAULT_BUY_IN)
  })
})
