import type { ReactElement } from 'react'
import type { Card as CardModel } from '../engine/types'

const RANK_LABELS: Record<CardModel['rank'], string> = {
  2: '2',
  3: '3',
  4: '4',
  5: '5',
  6: '6',
  7: '7',
  8: '8',
  9: '9',
  10: '10',
  11: 'J',
  12: 'Q',
  13: 'K',
  14: 'A',
}

const SUIT_SYMBOLS: Record<CardModel['suit'], string> = {
  clubs: '♣',
  diamonds: '♦',
  hearts: '♥',
  spades: '♠',
}

const RED_SUITS: ReadonlySet<CardModel['suit']> = new Set(['diamonds', 'hearts'])

interface CardProps {
  card: CardModel
}

export const Card = ({ card }: CardProps): ReactElement => {
  const isRed = RED_SUITS.has(card.suit)
  return (
    <div className={`card${isRed ? ' card--red' : ''}`} aria-label={`${RANK_LABELS[card.rank]} of ${card.suit}`}>
      {RANK_LABELS[card.rank]}
      {SUIT_SYMBOLS[card.suit]}
    </div>
  )
}

export const CardBack = (): ReactElement => (
  <div className="card card--back" aria-label="face-down card">
    ?
  </div>
)
