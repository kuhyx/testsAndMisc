import type { Seat, Street } from './types'

export type Action =
  | { type: 'fold' }
  | { type: 'check' }
  | { type: 'call' }
  | { type: 'bet'; amount: number }
  | { type: 'raise'; amount: number }

export interface SeatState {
  stack: number
  committed: number // chips this seat has put in during the CURRENT betting round
  hasActed: boolean
  folded: boolean
  allIn: boolean
}

export interface BettingState {
  street: Street
  pot: number // chips committed in PREVIOUS rounds, not yet including this round
  toAct: Seat
  seats: Record<Seat, SeatState>
  betToCall: number // highest `committed` this round
  minRaiseSize: number // minimum additional amount a raise must add beyond a call, per no-limit rules
  roundOver: boolean
}

const other = (seat: Seat): Seat => (seat === 'player' ? 'opponent' : 'player')

/**
 * Chips this seat still needs to add to match betToCall.
 *
 * The `Math.max(0, ...)` floor is defensive only: `applyAction` always sets `betToCall` to the
 * highest `committed` in the round, so no seat's `committed` can exceed it and the subtraction is
 * never negative in practice — the full suite passes with the floor removed. It stays because it
 * costs nothing and makes the "never negative" contract local to this function rather than an
 * invariant a reader has to reconstruct from every `betToCall` write site.
 */
const owedToCall = (state: BettingState, seat: Seat): number =>
  Math.max(0, state.betToCall - state.seats[seat].committed)

/** Generates the legal actions for the seat to act. Illegal actions are never representable in the UI. */
export const legalActions = (state: BettingState): readonly Action[] => {
  if (state.roundOver) {
    return []
  }
  const actor = state.seats[state.toAct]
  if (actor.folded || actor.allIn) {
    return []
  }

  const toCall = owedToCall(state, state.toAct)
  const actions: Action[] = [{ type: 'fold' }]

  if (toCall === 0) {
    actions.push({ type: 'check' })
  } else {
    actions.push({ type: 'call' })
  }

  const maxAdditional = actor.stack
  const minOpenOrRaiseAdditional = toCall + state.minRaiseSize
  if (maxAdditional > toCall) {
    const kind = state.betToCall === 0 ? 'bet' : 'raise'
    const minAdditional = Math.min(minOpenOrRaiseAdditional, maxAdditional)
    // Every legal size from the minimum up to an all-in is available; expose min and all-in as
    // concrete options rather than an open-ended range, since the UI drives a discrete control.
    actions.push({ type: kind, amount: minAdditional })
    if (maxAdditional > minAdditional) {
      actions.push({ type: kind, amount: maxAdditional })
    }
  }

  return actions
}

const applyChips = (seat: SeatState, additional: number): SeatState => {
  const spend = Math.min(additional, seat.stack)
  return {
    ...seat,
    stack: seat.stack - spend,
    committed: seat.committed + spend,
    allIn: seat.stack - spend === 0,
  }
}

/** Applies an action, returning the next BettingState. Assumes the action came from legalActions(state). */
export const applyAction = (state: BettingState, action: Action): BettingState => {
  const actingSeat = state.toAct
  const opponentSeat = other(actingSeat)

  if (action.type === 'fold') {
    return {
      ...state,
      seats: { ...state.seats, [actingSeat]: { ...state.seats[actingSeat], folded: true, hasActed: true } },
      roundOver: true,
    }
  }

  if (action.type === 'check') {
    const nextSeats: Record<Seat, SeatState> = {
      ...state.seats,
      [actingSeat]: { ...state.seats[actingSeat], hasActed: true },
    }
    const bothActed = nextSeats[opponentSeat].hasActed
    return { ...state, seats: nextSeats, toAct: opponentSeat, roundOver: bothActed }
  }

  if (action.type === 'call') {
    const toCall = owedToCall(state, actingSeat)
    const nextSeats: Record<Seat, SeatState> = {
      ...state.seats,
      [actingSeat]: { ...applyChips(state.seats[actingSeat], toCall), hasActed: true },
    }
    // A call closes the round UNLESS the other seat has never acted this round yet (the
    // heads-up big-blind-option case: SB completes preflop, BB still gets first say).
    const bothActed = nextSeats[opponentSeat].hasActed
    return { ...state, seats: nextSeats, toAct: opponentSeat, roundOver: bothActed }
  }

  // bet or raise
  const nextActingSeatState: SeatState = {
    ...applyChips(state.seats[actingSeat], action.amount),
    hasActed: true,
  }
  const raiseSize = nextActingSeatState.committed - state.betToCall
  return {
    ...state,
    seats: {
      ...state.seats,
      [actingSeat]: nextActingSeatState,
      [opponentSeat]: { ...state.seats[opponentSeat], hasActed: false },
    },
    betToCall: nextActingSeatState.committed,
    minRaiseSize: Math.max(state.minRaiseSize, raiseSize),
    toAct: opponentSeat,
    roundOver: false,
  }
}
