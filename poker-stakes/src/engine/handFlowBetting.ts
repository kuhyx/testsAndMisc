import type { BettingState, SeatState } from './bettingRound'
import type { Seat, Street } from './types'
import type { HandSetup, HeadsUpStacks } from './handFlow'

/**
 * Betting-state helpers for handFlow, split out to stay under the 250-line cap.
 */

export const other = (seat: Seat): Seat => (seat === 'player' ? 'opponent' : 'player')

export const STREET_ORDER: readonly Street[] = ['preflop', 'flop', 'turn', 'river']

export const initialBettingState = (setup: HandSetup, street: Street, pot: number, stacks: HeadsUpStacks): BettingState => {
  const nonButton = other(setup.buttonSeat)
  // A seat already at 0 chips (all-in from an earlier street's blind/bet) stays all-in on every
  // later street — a fresh `allIn: false` here would wrongly offer fold/check on a 0 stack.
  const buttonSeat: SeatState = {
    stack: stacks[setup.buttonSeat],
    committed: 0,
    hasActed: false,
    folded: false,
    allIn: stacks[setup.buttonSeat] === 0,
  }
  const nonButtonSeat: SeatState = {
    stack: stacks[nonButton],
    committed: 0,
    hasActed: false,
    folded: false,
    allIn: stacks[nonButton] === 0,
  }

  if (street === 'preflop') {
    // Heads-up: button posts small blind and acts FIRST preflop.
    const buttonPosted: SeatState = { ...buttonSeat, ...postBlind(buttonSeat, setup.smallBlind) }
    const nonButtonPosted: SeatState = { ...nonButtonSeat, ...postBlind(nonButtonSeat, setup.bigBlind) }
    return {
      street,
      pot,
      toAct: setup.buttonSeat,
      seats: { [setup.buttonSeat]: buttonPosted, [nonButton]: nonButtonPosted } as Record<Seat, SeatState>,
      betToCall: nonButtonPosted.committed,
      minRaiseSize: setup.bigBlind,
      roundOver: false,
    }
  }

  // Postflop: non-button (big blind) acts first.
  return {
    street,
    pot,
    toAct: nonButton,
    seats: { [setup.buttonSeat]: buttonSeat, [nonButton]: nonButtonSeat } as Record<Seat, SeatState>,
    betToCall: 0,
    minRaiseSize: setup.bigBlind,
    roundOver: false,
  }
}

export const postBlind = (seatState: SeatState, amount: number): SeatState => {
  const spend = Math.min(amount, seatState.stack)
  return { stack: seatState.stack - spend, committed: spend, hasActed: false, folded: false, allIn: seatState.stack - spend === 0 }
}

/** Returns the uncalled excess of the seat with the higher committed amount, and the state with it returned. */
export const returnUncalledExcess = (betting: BettingState): BettingState => {
  const { player, opponent } = betting.seats
  if (player.committed === opponent.committed) {
    return betting
  }
  const [higher, higherSeat, lowerCommitted] =
    player.committed > opponent.committed ? [player, 'player' as Seat, opponent.committed] : [opponent, 'opponent' as Seat, player.committed]
  const excess = higher.committed - lowerCommitted
  return {
    ...betting,
    seats: {
      ...betting.seats,
      [higherSeat]: { ...higher, committed: higher.committed - excess, stack: higher.stack + excess },
    },
  }
}

/** The live pot, including both seats' amounts committed on the current street (not yet swept into `betting.pot`). */
export const potFromBetting = (betting: BettingState): number =>
  betting.pot + betting.seats.player.committed + betting.seats.opponent.committed

export const stacksFromBetting = (betting: BettingState): HeadsUpStacks => ({
  player: betting.seats.player.stack,
  opponent: betting.seats.opponent.stack,
})
