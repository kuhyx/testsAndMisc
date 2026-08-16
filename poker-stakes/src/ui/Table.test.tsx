import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { startInteractiveHand } from '../engine/interactiveHand'
import { createRng } from '../engine/rng'
import type { SessionState } from '../engine/session'
import type { HandPhase } from './useGame'
import { Table } from './Table'

const session: SessionState = {
  stacks: { player: 200, opponent: 200 },
  buttonSeat: 'player',
  handsPlayed: 0,
  outcome: null,
}

describe('Table', () => {
  it('shows the player their own hole cards and hides the opponent behind card backs mid-hand', () => {
    const hand = startInteractiveHand(
      createRng(1),
      createRng(1 ^ 0x9e3779b9),
      { buttonSeat: 'player', bigBlind: 10, smallBlind: 5, stacks: { player: 200, opponent: 200 } },
      1,
    )
    if (hand.status.kind !== 'awaiting') {
      throw new Error('expected an awaiting hand for this seed')
    }
    const handPhase: HandPhase = { kind: 'awaiting', step: hand.status.step }
    render(<Table session={session} handPhase={handPhase} />)
    expect(screen.getAllByLabelText(/face-down card/)).toHaveLength(2)
    // Two own hole cards render as real Card elements, not face-down.
    const allCards = screen.getAllByLabelText(/ of /)
    expect(allCards.length).toBeGreaterThanOrEqual(2)
  })

  it('hides the opponent when betweenHands after a fold (no reveal)', () => {
    const handPhase: HandPhase = {
      kind: 'betweenHands',
      lastResult: {
        winner: 'opponent',
        potAwarded: 15,
        wentToShowdown: false,
        finalStacks: { player: 190, opponent: 210 },
        loserSeat: 'player',
        board: [],
        revealedHoleCards: null,
      },
    }
    render(<Table session={session} handPhase={handPhase} />)
    expect(screen.queryByLabelText(/face-down card/)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/ of /)).not.toBeInTheDocument()
  })

  it('reveals both hole cards at a showdown result while betweenHands', () => {
    const handPhase: HandPhase = {
      kind: 'betweenHands',
      lastResult: {
        winner: 'player',
        potAwarded: 40,
        wentToShowdown: true,
        finalStacks: { player: 220, opponent: 180 },
        loserSeat: 'opponent',
        board: [
          { rank: 2, suit: 'clubs' },
          { rank: 5, suit: 'diamonds' },
          { rank: 9, suit: 'hearts' },
        ],
        revealedHoleCards: {
          player: [
            { rank: 14, suit: 'spades' },
            { rank: 14, suit: 'clubs' },
          ],
          opponent: [
            { rank: 3, suit: 'hearts' },
            { rank: 4, suit: 'spades' },
          ],
        },
      },
    }
    render(<Table session={session} handPhase={handPhase} />)
    // The opponent's revealed hand.
    expect(screen.getByLabelText('3 of hearts')).toBeInTheDocument()
    expect(screen.getByLabelText('4 of spades')).toBeInTheDocument()
    // ...and your OWN hand, which must stay visible after the hand resolves — otherwise a
    // showdown shows the opponent's cards and the board while your seat sits empty and you
    // cannot see what you won or lost with. This is what "both" in the test name means.
    expect(screen.getByLabelText('A of spades')).toBeInTheDocument()
    expect(screen.getByLabelText('A of clubs')).toBeInTheDocument()
    // Board cards render too.
    expect(screen.getByLabelText('9 of hearts')).toBeInTheDocument()
  })

  it('leaves your seat empty after a fold, since no hand is revealed then', () => {
    const handPhase: HandPhase = {
      kind: 'betweenHands',
      lastResult: {
        winner: 'opponent',
        potAwarded: 15,
        wentToShowdown: false,
        finalStacks: { player: 190, opponent: 210 },
        loserSeat: 'player',
        board: [],
        revealedHoleCards: null,
      },
    }
    render(<Table session={session} handPhase={handPhase} />)
    expect(screen.queryByLabelText(/ of /)).not.toBeInTheDocument()
  })

  it('reads stacks and pot=0 from session when handPhase is null (pre-first-hand transient)', () => {
    render(<Table session={session} handPhase={null} />)
    expect(screen.getByText('Pot: 0')).toBeInTheDocument()
    expect(screen.getByText('You — 200 chips')).toBeInTheDocument()
    expect(screen.getByText('Opponent — 200 chips')).toBeInTheDocument()
  })
})
