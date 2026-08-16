import type { ReactElement } from 'react'
import type { SessionState } from '../engine/session'
import type { BuyIn } from '../stakes/types'
import type { HandPhase } from './useGame'

interface CashOutPanelProps {
  session: SessionState
  buyIn: BuyIn
  handPhase: HandPhase | null
  onCashOut: () => void
}

/**
 * Visible only between hands — mid-hand `session.stacks` is a stale pre-hand snapshot, and
 * `useGame.cashOut` itself refuses mid-hand (the settlement-exploit fix), so this mirrors that
 * restriction rather than showing a button that would silently do nothing when clicked.
 */
export const CashOutPanel = ({ session, buyIn, handPhase, onCashOut }: CashOutPanelProps): ReactElement | null => {
  if (handPhase?.kind !== 'betweenHands') {
    return null
  }
  const owedIfCashedOutNow = Math.max(0, 2 * buyIn.chips - session.stacks.player)
  return (
    <div className="panel">
      <p>
        Current stack: {session.stacks.player} chips. Cashing out now would owe {owedIfCashedOutNow} units.
      </p>
      <button type="button" className="button button--danger" onClick={onCashOut}>
        Leave table
      </button>
    </div>
  )
}
