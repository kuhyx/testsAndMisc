/** Card ranks, stored high (Ace = 14). Wheel straights are handled explicitly in handEval. */
export type Rank = 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14

export type Suit = 'clubs' | 'diamonds' | 'hearts' | 'spades'

export interface Card {
  rank: Rank
  suit: Suit
}

export type Seat = 'player' | 'opponent'

export type Street = 'preflop' | 'flop' | 'turn' | 'river' | 'showdown'
