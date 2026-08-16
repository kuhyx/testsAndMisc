import type { ReactElement } from 'react'
import { potFromBetting } from '../engine/handFlow'
import type { SessionState } from '../engine/session'
import type { Card as CardModel } from '../engine/types'
import type { HandPhase } from './useGame'
import { Card, CardBack } from './Card'

interface TableProps {
  session: SessionState
  handPhase: HandPhase | null
}

/** Stable per-hand key: a hand never contains a duplicate card, so rank+suit uniquely identifies one. */
const cardKey = (card: CardModel): string => `${String(card.rank)}-${card.suit}`

/**
 * Reads stacks/pot from the live source of truth for the current moment: `handPhase.step.betting`
 * mid-hand (which reflects THIS hand's blinds/bets — `session.stacks` is still the pre-hand
 * snapshot then), and `session.stacks` between hands (pot is 0, no betting state exists).
 */
export const Table = ({ session, handPhase }: TableProps): ReactElement => {
  const isAwaiting = handPhase?.kind === 'awaiting'
  const betting = isAwaiting ? handPhase.step.betting : null
  const stacks = betting === null ? session.stacks : { player: betting.seats.player.stack, opponent: betting.seats.opponent.stack }
  const pot = betting === null ? 0 : potFromBetting(betting)
  const board = isAwaiting ? handPhase.step.board : (handPhase?.kind === 'betweenHands' ? handPhase.lastResult?.board : undefined) ?? []
  const revealed = handPhase?.kind === 'betweenHands' ? (handPhase.lastResult?.revealedHoleCards ?? null) : null
  const revealedOpponentCards = revealed?.opponent ?? null
  // Your own hand stays visible after the hand resolves, not just while a decision is pending —
  // otherwise a showdown shows the opponent's cards and the board while your seat sits empty, and
  // you cannot see what you actually won or lost with.
  const playerHoleCards = isAwaiting ? handPhase.step.ownHoleCards : (revealed?.player ?? null)

  return (
    <div className="table">
      <div className="table__seat">
        <span>Opponent — {stacks.opponent} chips</span>
        <div className="table__cards">
          {revealedOpponentCards !== null
            ? revealedOpponentCards.map((card) => <Card key={cardKey(card)} card={card} />)
            : isAwaiting && (
                <>
                  <CardBack />
                  <CardBack />
                </>
              )}
        </div>
      </div>

      <div className="table__pot">Pot: {pot}</div>

      <div className="table__cards">
        {board.map((card) => (
          <Card key={cardKey(card)} card={card} />
        ))}
      </div>

      <div className="table__seat">
        <div className="table__cards">
          {playerHoleCards?.map((card) => <Card key={cardKey(card)} card={card} />)}
        </div>
        <span>You — {stacks.player} chips</span>
      </div>
    </div>
  )
}
