import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { DebtLoad } from '../stakes/storage'
import type { SettledDebt } from '../stakes/types'
import { DebtHistoryPanel } from './DebtHistoryPanel'

const debt = (overrides: Partial<SettledDebt> = {}): SettledDebt => ({
  id: 'd1',
  taskTypeId: 'pushups',
  owedUnits: 100,
  reason: 'cashOut',
  settledAt: 1,
  paidUnits: 0,
  ...overrides,
})

describe('DebtHistoryPanel', () => {
  it('says so when nothing has been settled yet', () => {
    render(<DebtHistoryPanel debtLoad={{ status: 'ok', debts: [] }} onLogDebtProgress={vi.fn()} />)
    expect(screen.getByText('No debts settled yet.')).toBeInTheDocument()
  })

  it('reports unreadable storage instead of an empty ledger (fail-closed)', () => {
    render(<DebtHistoryPanel debtLoad={{ status: 'unreadable' }} onLogDebtProgress={vi.fn()} />)
    expect(screen.getByText('Your debt history could not be read.')).toBeInTheDocument()
    expect(screen.queryByText('No debts settled yet.')).not.toBeInTheDocument()
  })

  it('gives an outstanding debt the log-progress control', async () => {
    const user = userEvent.setup()
    const onLogDebtProgress = vi.fn()
    const debtLoad: DebtLoad = { status: 'ok', debts: [debt({ owedUnits: 100, paidUnits: 40 })] }
    render(<DebtHistoryPanel debtLoad={debtLoad} onLogDebtProgress={onLogDebtProgress} />)
    expect(screen.getByText('Pushups: 40 / 100 done')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Log units done for Pushups'), '10')
    await user.click(screen.getByText('Log progress'))
    expect(onLogDebtProgress).toHaveBeenCalledWith('d1', 10)
  })

  it('renders a cleared debt as read-only history with its reason', () => {
    const debtLoad: DebtLoad = { status: 'ok', debts: [debt({ owedUnits: 50, paidUnits: 50, reason: 'bust' })] }
    render(<DebtHistoryPanel debtLoad={debtLoad} onLogDebtProgress={vi.fn()} />)
    expect(screen.getByText('Pushups: 50 owed (bust) — cleared')).toBeInTheDocument()
    expect(screen.queryByText('Log progress')).not.toBeInTheDocument()
  })

  it('labels a cash-out reason distinctly from a bust', () => {
    const debtLoad: DebtLoad = { status: 'ok', debts: [debt({ owedUnits: 50, paidUnits: 50, reason: 'cashOut' })] }
    render(<DebtHistoryPanel debtLoad={debtLoad} onLogDebtProgress={vi.fn()} />)
    expect(screen.getByText('Pushups: 50 owed (cashed out) — cleared')).toBeInTheDocument()
  })

  // A doubled-up session settles to owedUnits 0, which is already cleared at settle time.
  it('treats a zero-owed debt as cleared', () => {
    const debtLoad: DebtLoad = { status: 'ok', debts: [debt({ owedUnits: 0, paidUnits: 0 })] }
    render(<DebtHistoryPanel debtLoad={debtLoad} onLogDebtProgress={vi.fn()} />)
    expect(screen.getByText('Pushups: 0 owed (cashed out) — cleared')).toBeInTheDocument()
  })

  it('lists debts newest first regardless of stored order', () => {
    const debtLoad: DebtLoad = {
      status: 'ok',
      debts: [
        debt({ id: 'old', taskTypeId: 'anki', owedUnits: 10, paidUnits: 10, settledAt: 100 }),
        debt({ id: 'new', taskTypeId: 'leetcode', owedUnits: 20, paidUnits: 20, settledAt: 900 }),
      ],
    }
    render(<DebtHistoryPanel debtLoad={debtLoad} onLogDebtProgress={vi.fn()} />)
    const rows = screen.getAllByRole('listitem').map((li) => li.textContent)
    expect(rows[0]).toContain('LeetCode problems')
    expect(rows[1]).toContain('Anki reviews')
  })
})
