import type { Action, BettingState, SeatState } from './bettingRound'
import { applyAction, legalActions } from './bettingRound'
import { createDealCursor, dealCards, shuffleDeck } from './deck'
import { buildDeck } from './deck'
import { compareHandScore, evaluate7 } from './handEval'
import type { HandScore } from './handEval'
import type { Rng } from './rng'
import type { Card, Seat, Street } from './types'

export interface HeadsUpStacks {
  player: number
  opponent: number
}

export interface HandSetup {
  buttonSeat: Seat // heads-up: button posts the small blind and acts first preflop
  bigBlind: number
  smallBlind: number
  stacks: HeadsUpStacks
}

export interface HandResult {
  winner: Seat | 'split'
  potAwarded: number
  wentToShowdown: boolean
  finalStacks: HeadsUpStacks
  loserSeat: Seat | null
  board: readonly Card[]
  /** Both seats' hole cards, but ONLY at a real showdown — a folder's cards are never revealed. */
  revealedHoleCards: Record<Seat, readonly Card[]> | null
}

const other = (seat: Seat): Seat => (seat === 'player' ? 'opponent' : 'player')

const STREET_ORDER: readonly Street[] = ['preflop', 'flop', 'turn', 'river']

const initialBettingState = (setup: HandSetup, street: Street, pot: number, stacks: HeadsUpStacks): BettingState => {
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

const postBlind = (seatState: SeatState, amount: number): SeatState => {
  const spend = Math.min(amount, seatState.stack)
  return { stack: seatState.stack - spend, committed: spend, hasActed: false, folded: false, allIn: seatState.stack - spend === 0 }
}

/** Returns the uncalled excess of the seat with the higher committed amount, and the state with it returned. */
const returnUncalledExcess = (betting: BettingState): BettingState => {
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

const stacksFromBetting = (betting: BettingState): HeadsUpStacks => ({
  player: betting.seats.player.stack,
  opponent: betting.seats.opponent.stack,
})

export interface HandFlowCallbacks {
  /**
   * Called whenever it's a seat's turn; must return one of legalActions(betting). Receives ONLY
   * the acting seat's own hole cards — never the opponent's — so a decision function can never
   * see cards it shouldn't, by construction rather than by discipline.
   */
  decide: (betting: BettingState, seat: Seat, board: readonly Card[], ownHoleCards: readonly Card[]) => Action
}

/** One paused decision point within a hand: who must act, and on what they may see. */
export interface HandStep {
  betting: BettingState
  seat: Seat
  board: readonly Card[]
  ownHoleCards: readonly Card[]
}

/**
 * Runs a single hand end-to-end as a generator: posts blinds, deals hole cards, and pauses at
 * every decision point (`yield`ing a HandStep) instead of calling a callback directly. The caller
 * resumes it by passing the chosen Action into `.next(action)`. This lets a UI drive the hand one
 * decision at a time (suspend on the player's turn, wait for a click) without making the engine
 * itself async — it's suspension, not IO.
 */
export function* playHandSteps(rng: Rng, setup: HandSetup): Generator<HandStep, HandResult, Action> {
  const deck = shuffleDeck(rng, buildDeck())
  let cursor = createDealCursor(deck)

  const dealtPlayer = dealCards(cursor, 2)
  cursor = dealtPlayer.cursor
  const dealtOpponent = dealCards(cursor, 2)
  cursor = dealtOpponent.cursor
  const holeCards: Record<Seat, readonly Card[]> = {
    player: dealtPlayer.cards,
    opponent: dealtOpponent.cards,
  }

  let board: Card[] = []
  let betting = initialBettingState(setup, 'preflop', 0, setup.stacks)

  for (const street of STREET_ORDER) {
    if (street !== 'preflop') {
      const settled = returnUncalledExcess(betting)
      const communityCount = street === 'flop' ? 3 : 1
      const dealt = dealCards(cursor, communityCount)
      cursor = dealt.cursor
      board = [...board, ...dealt.cards]
      betting = initialBettingState(setup, street, potFromBetting(settled), stacksFromBetting(settled))
    }

    while (legalActions(betting).length > 0) {
      const action = yield { betting, seat: betting.toAct, board, ownHoleCards: holeCards[betting.toAct] }
      betting = applyAction(betting, action)
    }

    if (betting.seats.player.folded || betting.seats.opponent.folded) {
      return resolveByFold(betting, board)
    }
  }

  return resolveByShowdown(betting, board, holeCards)
}

/**
 * Runs a single hand end-to-end: posts blinds, deals hole cards, runs betting rounds interleaved
 * with community-card deals, and resolves the pot at fold or showdown. Thin synchronous driver
 * over `playHandSteps` for callers (tests, the PC-only path) that don't need to suspend mid-hand.
 */
export const playHand = (rng: Rng, setup: HandSetup, callbacks: HandFlowCallbacks): HandResult => {
  const gen = playHandSteps(rng, setup)
  let step = gen.next()
  while (!step.done) {
    const { betting, seat, board, ownHoleCards } = step.value
    step = gen.next(callbacks.decide(betting, seat, board, ownHoleCards))
  }
  return step.value
}

const resolveByFold = (betting: BettingState, board: readonly Card[]): HandResult => {
  const settled = returnUncalledExcess(betting)
  const pot = potFromBetting(settled)
  const loserSeat: Seat = settled.seats.player.folded ? 'player' : 'opponent'
  const winnerSeat = other(loserSeat)
  const finalStacks: HeadsUpStacks = {
    player: settled.seats.player.stack + (winnerSeat === 'player' ? pot : 0),
    opponent: settled.seats.opponent.stack + (winnerSeat === 'opponent' ? pot : 0),
  }
  // A folder's cards are never revealed, even to show what they held.
  return { winner: winnerSeat, potAwarded: pot, wentToShowdown: false, finalStacks, loserSeat, board, revealedHoleCards: null }
}

const resolveByShowdown = (
  betting: BettingState,
  board: readonly Card[],
  holeCards: Record<Seat, readonly Card[]>,
): HandResult => {
  const settled = returnUncalledExcess(betting)
  const pot = potFromBetting(settled)
  const playerCards = [...holeCards.player, ...board] as [Card, Card, Card, Card, Card, Card, Card]
  const opponentCards = [...holeCards.opponent, ...board] as [Card, Card, Card, Card, Card, Card, Card]
  const playerScore: HandScore = evaluate7(playerCards)
  const opponentScore: HandScore = evaluate7(opponentCards)
  const cmp = compareHandScore(playerScore, opponentScore)

  const stacks = stacksFromBetting(settled)
  if (cmp === 0) {
    // Split pot: heads-up play always returns uncalled excess before showdown, so both seats'
    // committed amounts are equal and the pot is provably even — no odd-chip remainder rule needed.
    const half = pot / 2
    return {
      winner: 'split',
      potAwarded: pot,
      wentToShowdown: true,
      finalStacks: {
        player: stacks.player + half,
        opponent: stacks.opponent + half,
      },
      loserSeat: null,
      board,
      revealedHoleCards: holeCards,
    }
  }

  const winnerSeat: Seat = cmp > 0 ? 'player' : 'opponent'
  const loserSeat = other(winnerSeat)
  return {
    winner: winnerSeat,
    potAwarded: pot,
    wentToShowdown: true,
    finalStacks: {
      player: stacks.player + (winnerSeat === 'player' ? pot : 0),
      opponent: stacks.opponent + (winnerSeat === 'opponent' ? pot : 0),
    },
    loserSeat,
    board,
    revealedHoleCards: holeCards,
  }
}
