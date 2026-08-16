import { useState } from 'react'
import type { ChangeEvent, ReactElement, SubmitEvent } from 'react'
import type { SettledDebt } from '../stakes/types'
import { taskLabel } from './taskLabel'

interface OutstandingDebtRowProps {
  debt: SettledDebt
  onLogDebtProgress: (debtId: string, units: number) => void
}

/**
 * Shared by `BuyInScreen` (the hard gate) and `DebtHistoryPanel` (the ledger) so the two can never
 * drift apart — the plan's "log N units done" control is the only way `paidUnits` advances, and
 * there is deliberately no mark-paid checkbox to short-circuit it.
 */
export const OutstandingDebtRow = ({ debt, onLogDebtProgress }: OutstandingDebtRowProps): ReactElement => {
  const [units, setUnits] = useState('')

  const submit = (event: SubmitEvent<HTMLFormElement>): void => {
    event.preventDefault()
    const parsed = Number(units)
    if (!Number.isInteger(parsed) || parsed <= 0) {
      return
    }
    onLogDebtProgress(debt.id, parsed)
    setUnits('')
  }

  return (
    <li>
      <span>
        {taskLabel(debt.taskTypeId)}: {debt.paidUnits} / {debt.owedUnits} done
      </span>
      <form className="log-progress" onSubmit={submit}>
        <input
          type="number"
          min={1}
          value={units}
          onChange={(event: ChangeEvent<HTMLInputElement>) => {
            setUnits(event.target.value)
          }}
          aria-label={`Log units done for ${taskLabel(debt.taskTypeId)}`}
        />
        <button type="submit" className="button">
          Log progress
        </button>
      </form>
    </li>
  )
}
