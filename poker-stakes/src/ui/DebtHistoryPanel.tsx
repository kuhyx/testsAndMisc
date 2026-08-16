import type { ReactElement } from 'react'
import type { DebtLoad } from '../stakes/storage'
import type { SettledDebt } from '../stakes/types'
import { OutstandingDebtRow } from './OutstandingDebtRow'
import { taskLabel } from './taskLabel'

interface DebtHistoryPanelProps {
  debtLoad: DebtLoad
  onLogDebtProgress: (debtId: string, units: number) => void
}

const reasonLabel = (reason: SettledDebt['reason']): string => (reason === 'bust' ? 'bust' : 'cashed out')

/** Cleared debts are read-only history — there is no control to un-pay one. */
const ClearedDebtRow = ({ debt }: { debt: SettledDebt }): ReactElement => (
  <li>
    <span>
      {taskLabel(debt.taskTypeId)}: {debt.owedUnits} owed ({reasonLabel(debt.reason)}) — cleared
    </span>
  </li>
)

/**
 * The durable ledger, separate from any single session: every `SettledDebt` ever recorded, newest
 * first. Outstanding entries carry the same log-progress control `BuyInScreen`'s gate shows (the
 * shared `OutstandingDebtRow`), so progress can be logged from either place with identical rules.
 */
export const DebtHistoryPanel = ({ debtLoad, onLogDebtProgress }: DebtHistoryPanelProps): ReactElement => {
  if (debtLoad.status === 'unreadable') {
    return (
      <div className="panel">
        <h2>Debt history</h2>
        <p>Your debt history could not be read.</p>
      </div>
    )
  }

  if (debtLoad.debts.length === 0) {
    return (
      <div className="panel">
        <h2>Debt history</h2>
        <p>No debts settled yet.</p>
      </div>
    )
  }

  const newestFirst = [...debtLoad.debts].sort((a, b) => b.settledAt - a.settledAt)

  return (
    <div className="panel">
      <h2>Debt history</h2>
      <ul className="debt-list">
        {newestFirst.map((debt) =>
          debt.paidUnits < debt.owedUnits ? (
            <OutstandingDebtRow key={debt.id} debt={debt} onLogDebtProgress={onLogDebtProgress} />
          ) : (
            <ClearedDebtRow key={debt.id} debt={debt} />
          ),
        )}
      </ul>
    </div>
  )
}
