import type { Card } from '../engine/types'

/** Shared helpers for the handEval test files, split to stay under the 250-line cap. */

export const card = (rank: Card['rank'], suit: Card['suit']): Card => ({ rank, suit })


export const five = (cards: readonly Card[]): [Card, Card, Card, Card, Card] => {
  if (cards.length !== 5) {
    throw new Error('five: expected exactly 5 cards')
  }
  const [a, b, c, d, e] = cards
  return [a, b, c, d, e] as [Card, Card, Card, Card, Card]
}

export const seven = (cards: readonly Card[]): [Card, Card, Card, Card, Card, Card, Card] => {
  if (cards.length !== 7) {
    throw new Error('seven: expected exactly 7 cards')
  }
  const [a, b, c, d, e, f, g] = cards
  return [a, b, c, d, e, f, g] as [Card, Card, Card, Card, Card, Card, Card]
}

/** Generates all C(52,5) 5-card combinations from a 52-card deck as index tuples. */
export function* combinations5(length: number): Generator<readonly [number, number, number, number, number]> {
  for (let a = 0; a < length; a += 1) {
    for (let b = a + 1; b < length; b += 1) {
      for (let c = b + 1; c < length; c += 1) {
        for (let d = c + 1; d < length; d += 1) {
          for (let e = d + 1; e < length; e += 1) {
            yield [a, b, c, d, e]
          }
        }
      }
    }
  }
}
