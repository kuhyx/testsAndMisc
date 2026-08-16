import { useState } from 'react'
import type { ChangeEvent, ReactElement, SubmitEvent } from 'react'
import { TASK_TYPES } from '../stakes/taskTypes'
import type { BuyIn } from '../stakes/types'
import type { DebtLoad } from '../stakes/storage'
import { OutstandingDebtRow } from './OutstandingDebtRow'
import { hasOutstandingDebt } from './useGame'

interface BuyInScreenProps {
  debtLoad: DebtLoad
  onBuyIn: (buyIn: BuyIn) => void
  onLogDebtProgress: (debtId: string, units: number) => void
}

/**
 * Hard gate, not a soft warning: while any debt is outstanding (or storage is unreadable, per the
 * fail-closed rule), the buy-in form is replaced entirely by the outstanding-debt list and a
 * log-progress control — matches the same gate `useGame.buyIn` enforces internally.
 */
export const BuyInScreen = ({ debtLoad, onBuyIn, onLogDebtProgress }: BuyInScreenProps): ReactElement => {
  const [taskTypeId, setTaskTypeId] = useState(TASK_TYPES[0].id)
  const [chips, setChips] = useState('100')

  if (debtLoad.status === 'unreadable') {
    return (
      <div className="panel">
        <p>Your debt history could not be read. Buying in is blocked until this is resolved.</p>
      </div>
    )
  }

  if (hasOutstandingDebt(debtLoad)) {
    const outstanding = debtLoad.debts.filter((d) => d.paidUnits < d.owedUnits)
    return (
      <div className="panel">
        <p>You have outstanding debt. Pay it off before buying into a new session.</p>
        <ul className="debt-list">
          {outstanding.map((debt) => (
            <OutstandingDebtRow key={debt.id} debt={debt} onLogDebtProgress={onLogDebtProgress} />
          ))}
        </ul>
      </div>
    )
  }

  const submit = (event: SubmitEvent<HTMLFormElement>): void => {
    event.preventDefault()
    const parsedChips = Number(chips)
    if (!Number.isInteger(parsedChips) || parsedChips <= 0) {
      return
    }
    onBuyIn({ taskTypeId, chips: parsedChips })
  }

  return (
    <form className="panel" onSubmit={submit}>
      <div className="field">
        <label htmlFor="task-type">Task type</label>
        <select
          id="task-type"
          value={taskTypeId}
          onChange={(event: ChangeEvent<HTMLSelectElement>) => {
            setTaskTypeId(event.target.value)
          }}
        >
          {TASK_TYPES.map((taskType) => (
            <option key={taskType.id} value={taskType.id}>
              {taskType.label}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="chip-count">Chip count</label>
        <input
          id="chip-count"
          type="number"
          min={1}
          step={1}
          value={chips}
          onChange={(event: ChangeEvent<HTMLInputElement>) => {
            setChips(event.target.value)
          }}
        />
      </div>
      <button type="submit" className="button button--primary">
        Sit down
      </button>
    </form>
  )
}
