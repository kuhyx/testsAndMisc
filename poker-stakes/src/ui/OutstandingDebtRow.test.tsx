import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { SettledDebt } from '../stakes/types'
import { OutstandingDebtRow } from './OutstandingDebtRow'

const debt = (overrides: Partial<SettledDebt> = {}): SettledDebt => ({
  id: 'd1',
  taskTypeId: 'pushups',
  owedUnits: 100,
  reason: 'cashOut',
  settledAt: 1,
  paidUnits: 40,
  ...overrides,
})

const renderRow = (overrides: Partial<SettledDebt> = {}): ReturnType<typeof vi.fn> => {
  const onLogDebtProgress = vi.fn()
  render(
    <ul>
      <OutstandingDebtRow debt={debt(overrides)} onLogDebtProgress={onLogDebtProgress} />
    </ul>,
  )
  return onLogDebtProgress
}

describe('OutstandingDebtRow', () => {
  it('shows progress against the owed amount', () => {
    renderRow()
    expect(screen.getByText('Pushups: 40 / 100 done')).toBeInTheDocument()
  })

  it('logs a positive integer of units and clears the field afterwards', async () => {
    const user = userEvent.setup()
    const onLogDebtProgress = renderRow()
    const input = screen.getByLabelText('Log units done for Pushups')
    await user.type(input, '20')
    await user.click(screen.getByText('Log progress'))
    expect(onLogDebtProgress).toHaveBeenCalledWith('d1', 20)
    expect(input).toHaveValue(null)
  })

  // Empty is the only non-positive value that reaches the JS guard — native `min={1}` validation
  // aborts submission for a typed "-5" or "0" before the handler runs.
  it('does not log when the units field is empty', async () => {
    const user = userEvent.setup()
    const onLogDebtProgress = renderRow()
    await user.click(screen.getByText('Log progress'))
    expect(onLogDebtProgress).not.toHaveBeenCalled()
  })

  it('does not log a fractional amount', async () => {
    const user = userEvent.setup()
    const onLogDebtProgress = renderRow()
    await user.type(screen.getByLabelText('Log units done for Pushups'), '2.5')
    await user.click(screen.getByText('Log progress'))
    expect(onLogDebtProgress).not.toHaveBeenCalled()
  })

  it('labels the input with the raw id when the task type is unknown', () => {
    renderRow({ taskTypeId: 'unknown-type' })
    expect(screen.getByLabelText('Log units done for unknown-type')).toBeInTheDocument()
  })
})
