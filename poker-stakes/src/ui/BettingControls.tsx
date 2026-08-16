import type { ReactElement } from 'react'
import type { Action, BettingState } from '../engine/bettingRound'
import { legalActions } from '../engine/bettingRound'

const ACTION_LABELS: Record<Action['type'], string> = {
  fold: 'Fold',
  check: 'Check',
  call: 'Call',
  bet: 'Bet',
  raise: 'Raise',
}

const actionKey = (action: Action): string =>
  action.type === 'bet' || action.type === 'raise' ? `${action.type}-${String(action.amount)}` : action.type

const actionLabel = (action: Action): string =>
  action.type === 'bet' || action.type === 'raise'
    ? `${ACTION_LABELS[action.type]} ${String(action.amount)}`
    : ACTION_LABELS[action.type]

interface BettingControlsProps {
  betting: BettingState
  onAction: (action: Action) => void
}

/** Renders exactly the legal-action set for the current betting state — illegal actions are never representable. */
export const BettingControls = ({ betting, onAction }: BettingControlsProps): ReactElement => {
  const actions = legalActions(betting)
  return (
    <div className="controls">
      {actions.map((action) => (
        <button
          key={actionKey(action)}
          type="button"
          className="button"
          onClick={() => {
            onAction(action)
          }}
        >
          {actionLabel(action)}
        </button>
      ))}
    </div>
  )
}
