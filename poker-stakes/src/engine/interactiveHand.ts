import type { Action } from './bettingRound'
import { legalActions } from './bettingRound'
import type { HandResult, HandSetup, HandStep } from './handFlow'
import { playHandSteps } from './handFlow'
import { decideAction } from './opponentPolicy'
import type { Rng } from './rng'
import type { Card } from './types'

/**
 * Exactly one of the two states holds at any time — a discriminated union instead of two
 * independently-nullable fields, so "both null" / "both set" are unrepresentable rather than
 * defensive-but-unreachable states a caller has to guard against.
 */
export type HandStatus = { kind: 'awaiting'; step: HandStep } | { kind: 'complete'; result: HandResult }

export interface InteractiveHand {
  readonly status: HandStatus
  /** Submits the player's action for the current `awaiting` step, resolves any opponent turns, and advances. */
  submit: (action: Action) => void
}

/**
 * Drives `playHandSteps` to completion, resolving every OPPONENT decision point internally via
 * `decideAction` (using its own policy RNG, separate from the dealing RNG so tuning `iterations`
 * never perturbs deal order) and only ever pausing at `status.step` on the PLAYER's turn. This is
 * the seam a UI drives: read `status`, call `submit(action)` on a click, repeat until `complete`.
 */
export const startInteractiveHand = (
  dealRng: Rng,
  policyRng: Rng,
  setup: HandSetup,
  opponentIterations: number,
): InteractiveHand => {
  const gen = playHandSteps(dealRng, setup)

  const advance = (next: IteratorResult<HandStep, HandResult>): HandStatus => {
    let step = next
    while (!step.done) {
      if (step.value.seat === 'player') {
        return { kind: 'awaiting', step: step.value }
      }
      const { betting, board, ownHoleCards } = step.value
      const legal = legalActions(betting)
      const ownHole = ownHoleCards as [Card, Card]
      const action = decideAction(betting, legal, ownHole, board, policyRng, opponentIterations)
      step = gen.next(action)
    }
    return { kind: 'complete', result: step.value }
  }

  let status: HandStatus = advance(gen.next())

  return {
    get status(): HandStatus {
      return status
    },
    submit: (action: Action): void => {
      if (status.kind !== 'awaiting') {
        throw new Error('startInteractiveHand: no player decision is pending')
      }
      status = advance(gen.next(action))
    },
  }
}
