import type { ReactElement } from 'react'
import type { HandResult } from '../engine/handFlow'

interface HandLogProps {
  lastResult: HandResult | null
}

const summarize = (result: HandResult): string => {
  const outcome = result.wentToShowdown ? 'at showdown' : 'by fold'
  const potAwarded = String(result.potAwarded)
  if (result.winner === 'split') {
    return `Split pot ${outcome} — ${potAwarded} chips divided evenly.`
  }
  const winnerLabel = result.winner === 'player' ? 'You won' : 'Opponent won'
  return `${winnerLabel} ${outcome} — ${potAwarded} chips.`
}

/** Shows the most recently completed hand's outcome — nothing until the first hand resolves. */
export const HandLog = ({ lastResult }: HandLogProps): ReactElement | null => {
  if (lastResult === null) {
    return null
  }
  return <p className="hand-log">{summarize(lastResult)}</p>
}
