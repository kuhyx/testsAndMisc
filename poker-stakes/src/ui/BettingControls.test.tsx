import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { BettingState, SeatState } from '../engine/bettingRound'
import { BettingControls } from './BettingControls'

const seat = (overrides: Partial<SeatState> = {}): SeatState => ({
  stack: 100,
  committed: 0,
  hasActed: false,
  folded: false,
  allIn: false,
  ...overrides,
})

const betting = (overrides: Partial<BettingState> = {}): BettingState => ({
  street: 'preflop',
  pot: 0,
  toAct: 'player',
  seats: { player: seat(), opponent: seat() },
  betToCall: 0,
  minRaiseSize: 10,
  roundOver: false,
  ...overrides,
})

describe('BettingControls', () => {
  it('renders fold/check/bet when nothing is owed', () => {
    render(<BettingControls betting={betting()} onAction={vi.fn()} />)
    expect(screen.getByText('Fold')).toBeInTheDocument()
    expect(screen.getByText('Check')).toBeInTheDocument()
    expect(screen.getByText('Bet 10')).toBeInTheDocument()
    expect(screen.getByText('Bet 100')).toBeInTheDocument()
    expect(screen.queryByText('Call')).not.toBeInTheDocument()
  })

  it('renders fold/call/raise when a bet is owed', () => {
    const state = betting({ betToCall: 20, seats: { player: seat(), opponent: seat({ committed: 20 }) } })
    render(<BettingControls betting={state} onAction={vi.fn()} />)
    expect(screen.getByText('Fold')).toBeInTheDocument()
    expect(screen.getByText('Call')).toBeInTheDocument()
    expect(screen.getByText('Raise 30')).toBeInTheDocument()
  })

  it('renders no bet/raise option when the acting seat cannot cover more than a call', () => {
    const state = betting({
      betToCall: 20,
      seats: { player: seat({ stack: 20 }), opponent: seat({ committed: 20 }) },
    })
    render(<BettingControls betting={state} onAction={vi.fn()} />)
    expect(screen.queryByText(/Raise/)).not.toBeInTheDocument()
  })

  it('calls onAction with the exact action when a button is clicked', async () => {
    const user = userEvent.setup()
    const onAction = vi.fn()
    render(<BettingControls betting={betting()} onAction={onAction} />)
    await user.click(screen.getByText('Check'))
    expect(onAction).toHaveBeenCalledWith({ type: 'check' })
    await user.click(screen.getByText('Bet 10'))
    expect(onAction).toHaveBeenCalledWith({ type: 'bet', amount: 10 })
  })
})
