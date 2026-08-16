import type { HandFlowCallbacks, HandResult, HeadsUpStacks } from './handFlow'
import { playHand } from './handFlow'
import type { Rng } from './rng'
import type { Seat } from './types'

export interface SessionConfig {
  buyInChips: number
}

export type SessionEndReason = 'cashOut' | 'bust'

export interface SessionOutcome {
  reason: SessionEndReason
  finalChips: number // the player's stack at the moment the session ended
}

export interface SessionState {
  stacks: HeadsUpStacks
  buttonSeat: Seat // rotates each hand
  handsPlayed: number
  outcome: SessionOutcome | null // null while the session is still live
}

/** Big blind derived from the buy-in; small blind is always ≥1 and strictly less than BB. */
export const deriveBlindSize = (buyInChips: number): { bigBlind: number; smallBlind: number } => {
  const bigBlind = Math.max(2, Math.floor(buyInChips / 100))
  const smallBlind = Math.floor(bigBlind / 2)
  return { bigBlind, smallBlind }
}

export const startSession = (config: SessionConfig): SessionState => ({
  stacks: { player: config.buyInChips, opponent: config.buyInChips },
  buttonSeat: 'player',
  handsPlayed: 0,
  outcome: null,
})

const other = (seat: Seat): Seat => (seat === 'player' ? 'opponent' : 'player')

/**
 * Folds a completed hand's result into the session: updates stacks, rotates the button, and
 * detects bust/cash-out. Pure — shared by `playSessionHand` (the PC-only synchronous path) and
 * any interactive driver that runs a hand via `playHandSteps` instead.
 */
export const applyHandResult = (session: SessionState, handResult: HandResult): SessionState => {
  const nextStacks = handResult.finalStacks
  // Player busting is a real debt event. Opponent busting means the player holds every chip in
  // play, which settles to owing nothing under the settlement formula — model it the same as a
  // cash-out (at the max chip count) rather than a special case, since no further hand is possible.
  let outcome: SessionOutcome | null = null
  if (nextStacks.player === 0) {
    outcome = { reason: 'bust', finalChips: 0 }
  } else if (nextStacks.opponent === 0) {
    outcome = { reason: 'cashOut', finalChips: nextStacks.player }
  }

  return {
    stacks: nextStacks,
    buttonSeat: other(session.buttonSeat),
    handsPlayed: session.handsPlayed + 1,
    outcome,
  }
}

/** Plays one hand, updates stacks, rotates the button, and detects bust. No-op if already ended. */
export const playSessionHand = (
  session: SessionState,
  rng: Rng,
  buyInChips: number,
  callbacks: HandFlowCallbacks,
): { session: SessionState; handResult: HandResult } => {
  if (session.outcome !== null) {
    throw new Error('playSessionHand: session has already ended')
  }
  const { bigBlind, smallBlind } = deriveBlindSize(buyInChips)
  const handResult = playHand(
    rng,
    { buttonSeat: session.buttonSeat, bigBlind, smallBlind, stacks: session.stacks },
    callbacks,
  )

  return { session: applyHandResult(session, handResult), handResult }
}

/** Ends a live session by cash-out, recording the player's current chip count. */
export const cashOutSession = (session: SessionState): SessionState => {
  if (session.outcome !== null) {
    throw new Error('cashOutSession: session has already ended')
  }
  return { ...session, outcome: { reason: 'cashOut', finalChips: session.stacks.player } }
}
