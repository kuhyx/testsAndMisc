import type { Action, BettingState } from './bettingRound'
import { buildDeck, shuffleDeck } from './deck'
import { compareHandScore, evaluate7 } from './handEval'
import type { Rng } from './rng'
import type { Card } from './types'

const cardKey = (card: Card): string => `${String(card.rank)}-${card.suit}`

/**
 * Monte Carlo equity estimate: samples `iterations` plausible completions of the unknown cards
 * (opponent's hole cards drawn from this seat's perspective, plus any remaining board cards) and
 * returns the fraction of samples this seat's final hand wins or ties.
 *
 * Only ever sees `ownHole` and the current `board` — never the real opponent's hole cards.
 */
export const estimateEquity = (
  ownHole: readonly [Card, Card],
  board: readonly Card[],
  rng: Rng,
  iterations: number,
): number => {
  const known = new Set([...ownHole, ...board].map(cardKey))
  const remaining = buildDeck().filter((card) => !known.has(cardKey(card)))
  const boardCardsNeeded = 5 - board.length

  let wins = 0
  for (let i = 0; i < iterations; i += 1) {
    const shuffled = shuffleDeck(rng, remaining)
    const opponentHole = shuffled.slice(0, 2) as [Card, Card]
    const remainingBoard = shuffled.slice(2, 2 + boardCardsNeeded)
    const fullBoard = [...board, ...remainingBoard]

    const ownSeven = [...ownHole, ...fullBoard] as [Card, Card, Card, Card, Card, Card, Card]
    const oppSeven = [...opponentHole, ...fullBoard] as [Card, Card, Card, Card, Card, Card, Card]
    const cmp = compareHandScore(evaluate7(ownSeven), evaluate7(oppSeven))
    if (cmp >= 0) {
      wins += 1
    }
  }
  return iterations === 0 ? 0 : wins / iterations
}

/**
 * Picks one of the legal actions using a hand-strength/pot-odds heuristic. Never constructs an
 * action outside `legal` — the returned action is always a member of that list.
 */
export const chooseAction = (legal: readonly Action[], equity: number, potOdds: number): Action => {
  const fold = legal.find((a) => a.type === 'fold')
  const passive = legal.find((a) => a.type === 'check' || a.type === 'call')
  const aggressiveActions = legal.filter((a) => a.type === 'bet' || a.type === 'raise')
  const minAggressive = aggressiveActions[0]
  const maxAggressive = aggressiveActions[aggressiveActions.length - 1]

  // Strong equity: bet/raise big when possible, otherwise take whatever passive/fold action is offered.
  if (equity >= 0.7 && maxAggressive !== undefined) {
    return maxAggressive
  }
  // Moderate equity: open/raise a standard (minimum) size when possible.
  if (equity >= 0.55 && minAggressive !== undefined) {
    return minAggressive
  }
  // Equity clears the price being laid: call/check rather than fold.
  if (equity >= potOdds && passive !== undefined) {
    return passive
  }
  // Equity doesn't justify continuing: fold if there's a cost to continue, else check for free.
  if (fold !== undefined) {
    return fold
  }
  if (passive !== undefined) {
    return passive
  }
  const fallback = legal[0]
  if (fallback === undefined) {
    throw new Error('chooseAction: no legal actions to choose from')
  }
  return fallback
}

/** Computes pot odds: the price (as equity fraction) required to profitably call the amount owed. */
export const potOddsToCall = (betting: BettingState): number => {
  const toCall = betting.betToCall - betting.seats[betting.toAct].committed
  if (toCall <= 0) {
    return 0
  }
  const potAfterCall = betting.pot + betting.seats.player.committed + betting.seats.opponent.committed + toCall
  return toCall / potAfterCall
}

/**
 * Composes estimateEquity + chooseAction into a full decision for the given betting state.
 * `ownHole` must be the deciding seat's own hole cards only.
 */
export const decideAction = (
  betting: BettingState,
  legal: readonly Action[],
  ownHole: readonly [Card, Card],
  board: readonly Card[],
  rng: Rng,
  iterations: number,
): Action => {
  const equity = estimateEquity(ownHole, board, rng, iterations)
  const potOdds = potOddsToCall(betting)
  return chooseAction(legal, equity, potOdds)
}
