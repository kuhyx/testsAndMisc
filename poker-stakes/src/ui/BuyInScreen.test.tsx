import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { DebtLoad } from '../stakes/storage'
import type { SettledDebt } from '../stakes/types'
import { BuyInScreen } from './BuyInScreen'

const debt = (overrides: Partial<SettledDebt> = {}): SettledDebt => ({
  id: 'd1',
  taskTypeId: 'pushups',
  owedUnits: 100,
  reason: 'cashOut',
  settledAt: 1,
  paidUnits: 0,
  ...overrides,
})

describe('BuyInScreen', () => {
  it('renders the buy-in form when there is no outstanding debt', () => {
    render(<BuyInScreen debtLoad={{ status: 'ok', debts: [] }} onBuyIn={vi.fn()} onLogDebtProgress={vi.fn()} />)
    expect(screen.getByText('Sit down')).toBeInTheDocument()
    expect(screen.queryByText(/outstanding debt/)).not.toBeInTheDocument()
  })

  it('submits the selected task type and chip count', async () => {
    const user = userEvent.setup()
    const onBuyIn = vi.fn()
    render(<BuyInScreen debtLoad={{ status: 'ok', debts: [] }} onBuyIn={onBuyIn} onLogDebtProgress={vi.fn()} />)
    const chipInput = screen.getByLabelText('Chip count')
    await user.clear(chipInput)
    await user.type(chipInput, '250')
    await user.click(screen.getByText('Sit down'))
    expect(onBuyIn).toHaveBeenCalledWith({ taskTypeId: 'pushups', chips: 250 })
  })

  // Passes because native `min={1}` validation aborts the submit, NOT because the JS guard ran —
  // the cleared-field test below is what actually exercises the guard. Keep both.
  it('does not submit a non-positive or fractional chip count', async () => {
    const user = userEvent.setup()
    const onBuyIn = vi.fn()
    render(<BuyInScreen debtLoad={{ status: 'ok', debts: [] }} onBuyIn={onBuyIn} onLogDebtProgress={vi.fn()} />)
    const chipInput = screen.getByLabelText('Chip count')
    await user.clear(chipInput)
    await user.type(chipInput, '0')
    await user.click(screen.getByText('Sit down'))
    expect(onBuyIn).not.toHaveBeenCalled()
  })

  // An empty field is the only non-positive value that actually reaches the JS guard: the
  // browser's native `min={1}` constraint aborts submission for a typed "-5"/"0" before the
  // handler fires, whereas an empty input is valid HTML-wise and parses to `Number('') === 0`.
  it('does not submit when the chip count is cleared to empty', async () => {
    const user = userEvent.setup()
    const onBuyIn = vi.fn()
    render(<BuyInScreen debtLoad={{ status: 'ok', debts: [] }} onBuyIn={onBuyIn} onLogDebtProgress={vi.fn()} />)
    await user.clear(screen.getByLabelText('Chip count'))
    await user.click(screen.getByText('Sit down'))
    expect(onBuyIn).not.toHaveBeenCalled()
  })

  it('buys in with the task type picked from the select', async () => {
    const user = userEvent.setup()
    const onBuyIn = vi.fn()
    render(<BuyInScreen debtLoad={{ status: 'ok', debts: [] }} onBuyIn={onBuyIn} onLogDebtProgress={vi.fn()} />)
    await user.selectOptions(screen.getByLabelText('Task type'), 'leetcode')
    await user.click(screen.getByText('Sit down'))
    expect(onBuyIn).toHaveBeenCalledWith({ taskTypeId: 'leetcode', chips: 100 })
  })

  it('replaces the buy-in form with outstanding debts when a debt is unpaid (hard gate)', () => {
    const debtLoad: DebtLoad = { status: 'ok', debts: [debt({ owedUnits: 100, paidUnits: 40 })] }
    render(<BuyInScreen debtLoad={debtLoad} onBuyIn={vi.fn()} onLogDebtProgress={vi.fn()} />)
    expect(screen.queryByText('Sit down')).not.toBeInTheDocument()
    expect(screen.getByText(/outstanding debt/)).toBeInTheDocument()
    expect(screen.getByText('Pushups: 40 / 100 done')).toBeInTheDocument()
  })

  it('does not list a fully paid debt among the outstanding ones', () => {
    const debtLoad: DebtLoad = {
      status: 'ok',
      debts: [debt({ id: 'paid', owedUnits: 50, paidUnits: 50 }), debt({ id: 'owed', owedUnits: 100, paidUnits: 0 })],
    }
    render(<BuyInScreen debtLoad={debtLoad} onBuyIn={vi.fn()} onLogDebtProgress={vi.fn()} />)
    expect(screen.queryByText('Pushups: 50 / 50 done')).not.toBeInTheDocument()
    expect(screen.getByText('Pushups: 0 / 100 done')).toBeInTheDocument()
  })

  it('a doubled-up debt (owedUnits 0) does not block a new buy-in', () => {
    const debtLoad: DebtLoad = { status: 'ok', debts: [debt({ owedUnits: 0, paidUnits: 0 })] }
    render(<BuyInScreen debtLoad={debtLoad} onBuyIn={vi.fn()} onLogDebtProgress={vi.fn()} />)
    expect(screen.getByText('Sit down')).toBeInTheDocument()
  })

  it('logs progress against an outstanding debt via the log-progress control', async () => {
    const user = userEvent.setup()
    const onLogDebtProgress = vi.fn()
    const debtLoad: DebtLoad = { status: 'ok', debts: [debt({ owedUnits: 100, paidUnits: 40 })] }
    render(<BuyInScreen debtLoad={debtLoad} onBuyIn={vi.fn()} onLogDebtProgress={onLogDebtProgress} />)
    const input = screen.getByLabelText('Log units done for Pushups')
    await user.type(input, '20')
    await user.click(screen.getByText('Log progress'))
    expect(onLogDebtProgress).toHaveBeenCalledWith('d1', 20)
  })

  // Passes because native `min={1}` validation aborts the submit, NOT because the JS guard ran —
  // the empty-field test below is what actually exercises the guard. Keep both.
  it('does not log a non-positive or fractional progress amount', async () => {
    const user = userEvent.setup()
    const onLogDebtProgress = vi.fn()
    const debtLoad: DebtLoad = { status: 'ok', debts: [debt({ owedUnits: 100, paidUnits: 40 })] }
    render(<BuyInScreen debtLoad={debtLoad} onBuyIn={vi.fn()} onLogDebtProgress={onLogDebtProgress} />)
    const input = screen.getByLabelText('Log units done for Pushups')
    await user.type(input, '-5')
    await user.click(screen.getByText('Log progress'))
    expect(onLogDebtProgress).not.toHaveBeenCalled()
  })

  // Same reasoning as the chip-count empty case: the empty field is what reaches the guard.
  it('does not log progress when the units field is left empty', async () => {
    const user = userEvent.setup()
    const onLogDebtProgress = vi.fn()
    const debtLoad: DebtLoad = { status: 'ok', debts: [debt({ owedUnits: 100, paidUnits: 40 })] }
    render(<BuyInScreen debtLoad={debtLoad} onBuyIn={vi.fn()} onLogDebtProgress={onLogDebtProgress} />)
    await user.click(screen.getByText('Log progress'))
    expect(onLogDebtProgress).not.toHaveBeenCalled()
  })

  it('blocks with a fail-closed message when storage was unreadable', () => {
    render(<BuyInScreen debtLoad={{ status: 'unreadable' }} onBuyIn={vi.fn()} onLogDebtProgress={vi.fn()} />)
    expect(screen.queryByText('Sit down')).not.toBeInTheDocument()
    expect(screen.getByText(/could not be read/)).toBeInTheDocument()
  })

  it('falls back to the raw taskTypeId label if it is not in the fixed list', () => {
    const debtLoad: DebtLoad = { status: 'ok', debts: [debt({ taskTypeId: 'unknown-type', owedUnits: 10, paidUnits: 0 })] }
    render(<BuyInScreen debtLoad={debtLoad} onBuyIn={vi.fn()} onLogDebtProgress={vi.fn()} />)
    expect(screen.getByText('unknown-type: 0 / 10 done')).toBeInTheDocument()
  })
})
