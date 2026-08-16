import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { HandResult } from '../engine/handFlow'
import { HandLog } from './HandLog'

const result = (overrides: Partial<HandResult> = {}): HandResult => ({
  winner: 'player',
  potAwarded: 40,
  wentToShowdown: true,
  finalStacks: { player: 240, opponent: 160 },
  loserSeat: 'opponent',
  board: [],
  revealedHoleCards: null,
  ...overrides,
})

describe('HandLog', () => {
  it('renders nothing before any hand has completed', () => {
    const { container } = render(<HandLog lastResult={null} />)
    expect(container.textContent).toBe('')
  })

  it('summarizes a player win at showdown', () => {
    render(<HandLog lastResult={result({ winner: 'player', wentToShowdown: true, potAwarded: 40 })} />)
    expect(screen.getByText('You won at showdown — 40 chips.')).toBeInTheDocument()
  })

  it('summarizes an opponent win by fold', () => {
    render(<HandLog lastResult={result({ winner: 'opponent', wentToShowdown: false, potAwarded: 15 })} />)
    expect(screen.getByText('Opponent won by fold — 15 chips.')).toBeInTheDocument()
  })

  it('summarizes a split pot', () => {
    render(<HandLog lastResult={result({ winner: 'split', wentToShowdown: true, potAwarded: 60, loserSeat: null })} />)
    expect(screen.getByText('Split pot at showdown — 60 chips divided evenly.')).toBeInTheDocument()
  })
})
