import type { Action, BettingState } from './bettingRound'
import { applyAction, legalActions } from './bettingRound'
import { createDealCursor, dealCards, shuffleDeck } from './deck'
import { buildDeck } from './deck'
import { compareHandScore, evaluate7 } from './handEval'
import type { HandScore } from './handEval'
import type { Rng } from './rng'
import type { Card, Seat } from './types'

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

import {
  initialBettingState,
  other,
  potFromBetting,
  returnUncalledExcess,
  stacksFromBetting,
  STREET_ORDER,
} from './handFlowBetting'

export { potFromBetting } from './handFlowBetting'


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
