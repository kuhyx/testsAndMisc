import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Card as CardModel } from '../engine/types'
import { Card, CardBack } from './Card'

describe('Card', () => {
  it('renders a black-suit card without the red modifier', () => {
    const card: CardModel = { rank: 14, suit: 'spades' }
    render(<Card card={card} />)
    const el = screen.getByLabelText('A of spades')
    expect(el.className).not.toContain('card--red')
    expect(el.textContent).toBe('A♠')
  })

  it('renders a red-suit card with the red modifier', () => {
    const card: CardModel = { rank: 10, suit: 'hearts' }
    render(<Card card={card} />)
    const el = screen.getByLabelText('10 of hearts')
    expect(el.className).toContain('card--red')
    expect(el.textContent).toBe('10♥')
  })

  it('renders every rank label correctly', () => {
    const ranks: { rank: CardModel['rank']; label: string }[] = [
      { rank: 2, label: '2' },
      { rank: 9, label: '9' },
      { rank: 10, label: '10' },
      { rank: 11, label: 'J' },
      { rank: 12, label: 'Q' },
      { rank: 13, label: 'K' },
      { rank: 14, label: 'A' },
    ]
    for (const { rank, label } of ranks) {
      const { unmount } = render(<Card card={{ rank, suit: 'clubs' }} />)
      expect(screen.getByText(`${label}♣`)).toBeInTheDocument()
      unmount()
    }
  })
})

describe('CardBack', () => {
  it('renders a face-down placeholder', () => {
    render(<CardBack />)
    expect(screen.getByLabelText('face-down card')).toBeInTheDocument()
  })
})
