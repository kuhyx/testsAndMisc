import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { HandStep } from '../engine/handFlow'
import type { SessionState } from '../engine/session'
import type { BuyIn } from '../stakes/types'
import type { HandPhase } from './useGame'
import { CashOutPanel } from './CashOutPanel'

const session = (playerStack: number): SessionState => ({
  stacks: { player: playerStack, opponent: 200 },
  buttonSeat: 'player',
  handsPlayed: 1,
  outcome: null,
})

const buyIn: BuyIn = { taskTypeId: 'pushups', chips: 100 }

describe('CashOutPanel', () => {
  it('renders nothing while a hand is in progress (mirrors the mid-hand cashOut refusal)', () => {
    const awaitingPhase: HandPhase = { kind: 'awaiting', step: {} as HandStep }
    const { container } = render(
      <CashOutPanel session={session(150)} buyIn={buyIn} handPhase={awaitingPhase} onCashOut={vi.fn()} />,
    )
    expect(container.textContent).toBe('')
  })

  it('renders nothing when handPhase is null (no live session yet)', () => {
    const { container } = render(<CashOutPanel session={session(100)} buyIn={buyIn} handPhase={null} onCashOut={vi.fn()} />)
    expect(container.textContent).toBe('')
  })

  it('shows a zero owed preview when the player has doubled their buy-in', () => {
    const phase: HandPhase = { kind: 'betweenHands', lastResult: null }
    render(<CashOutPanel session={session(200)} buyIn={buyIn} handPhase={phase} onCashOut={vi.fn()} />)
    expect(screen.getByText(/owe 0 units/)).toBeInTheDocument()
  })

  it('shows the correct owed preview for a partial loss', () => {
    const phase: HandPhase = { kind: 'betweenHands', lastResult: null }
    render(<CashOutPanel session={session(50)} buyIn={buyIn} handPhase={phase} onCashOut={vi.fn()} />)
    // owed = max(0, 2*100 - 50) = 150
    expect(screen.getByText(/owe 150 units/)).toBeInTheDocument()
  })

  it('calls onCashOut when the leave-table button is clicked', async () => {
    const user = userEvent.setup()
    const onCashOut = vi.fn()
    const phase: HandPhase = { kind: 'betweenHands', lastResult: null }
    render(<CashOutPanel session={session(120)} buyIn={buyIn} handPhase={phase} onCashOut={onCashOut} />)
    await user.click(screen.getByText('Leave table'))
    expect(onCashOut).toHaveBeenCalledOnce()
  })
})
