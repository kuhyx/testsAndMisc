import { describe, expect, it } from 'vitest'
import { legalActions } from './bettingRound'
import type { HandSetup } from './handFlow'
import { startInteractiveHand } from './interactiveHand'
import { createRng } from './rng'

const setup = (overrides: Partial<HandSetup> = {}): HandSetup => ({
  buttonSeat: 'player',
  bigBlind: 10,
  smallBlind: 5,
  stacks: { player: 200, opponent: 200 },
  ...overrides,
})

const totalStack = (setupArg: HandSetup): number => setupArg.stacks.player + setupArg.stacks.opponent

/** Drives an interactive hand to completion always checking/calling on the player's turns. */
const runToCompletion = (hand: ReturnType<typeof startInteractiveHand>): void => {
  while (hand.status.kind === 'awaiting') {
    const betting = hand.status.step.betting
    const toCall = betting.betToCall - betting.seats.player.committed
    hand.submit(toCall > 0 ? { type: 'call' } : { type: 'check' })
  }
}

describe('startInteractiveHand', () => {
  it('pauses on the player seat only, never surfacing the opponent as awaiting', () => {
    const s = setup()
    const hand = startInteractiveHand(createRng(1), createRng(1 ^ 0x9e3779b9), s, 1)
    expect(hand.status.kind).toBe('awaiting')
    if (hand.status.kind !== 'awaiting') {
      throw new Error('unreachable: asserted above')
    }
    expect(hand.status.step.seat).toBe('player')
  })

  it('every offered awaiting action is legal for the current betting state', () => {
    const s = setup()
    const hand = startInteractiveHand(createRng(1), createRng(1 ^ 0x9e3779b9), s, 1)
    while (hand.status.kind === 'awaiting') {
      const { step } = hand.status
      const legal = legalActions(step.betting)
      const toCall = step.betting.betToCall - step.betting.seats.player.committed
      const action = toCall > 0 ? { type: 'call' as const } : { type: 'check' as const }
      expect(legal).toContainEqual(action)
      hand.submit(action)
    }
  })

  it('runs a full hand to completion via alternating player submits and internal opponent turns', () => {
    const s = setup()
    const hand = startInteractiveHand(createRng(1), createRng(1 ^ 0x9e3779b9), s, 1)
    runToCompletion(hand)
    expect(hand.status.kind).toBe('complete')
    if (hand.status.kind !== 'complete') {
      throw new Error('unreachable: asserted above')
    }
    const { result } = hand.status
    expect(result.finalStacks.player + result.finalStacks.opponent).toBe(totalStack(s))
  })

  it('resolves a preflop player fold without ever pausing again', () => {
    const s = setup()
    const hand = startInteractiveHand(createRng(2), createRng(2 ^ 0x9e3779b9), s, 1)
    expect(hand.status.kind).toBe('awaiting')
    hand.submit({ type: 'fold' })
    expect(hand.status.kind).toBe('complete')
    if (hand.status.kind !== 'complete') {
      throw new Error('unreachable: asserted above')
    }
    expect(hand.status.result.loserSeat).toBe('player')
  })

  it('throws if submit is called with no decision pending', () => {
    const s = setup()
    const hand = startInteractiveHand(createRng(2), createRng(2 ^ 0x9e3779b9), s, 1)
    hand.submit({ type: 'fold' })
    expect(hand.status.kind).toBe('complete')
    expect(() => {
      hand.submit({ type: 'fold' })
    }).toThrow('no player decision is pending')
  })

  it('is deterministic for fixed deal and policy seeds', () => {
    const s = setup()
    const a = startInteractiveHand(createRng(1), createRng(1 ^ 0x9e3779b9), s, 1)
    runToCompletion(a)
    const b = startInteractiveHand(createRng(1), createRng(1 ^ 0x9e3779b9), s, 1)
    runToCompletion(b)
    expect(a.status).toEqual(b.status)
  })

  it('changing opponent iterations does not change the deal (dealRng and policyRng are independent)', () => {
    const s = setup()
    const collectBoards = (opponentIterations: number): unknown[] => {
      const hand = startInteractiveHand(createRng(1), createRng(1 ^ 0x9e3779b9), s, opponentIterations)
      const boards: unknown[] = []
      while (hand.status.kind === 'awaiting') {
        const { step } = hand.status
        boards.push(step.board)
        const toCall = step.betting.betToCall - step.betting.seats.player.committed
        hand.submit(toCall > 0 ? { type: 'call' } : { type: 'check' })
      }
      return boards
    }
    // Different iteration counts consume policyRng differently; if it leaked into dealing, the
    // board sequence collected at each player-decision pause would diverge between the two runs.
    expect(collectBoards(1)).toEqual(collectBoards(5))
  })
})
