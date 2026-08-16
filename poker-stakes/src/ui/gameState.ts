import type { HandResult, HandStep } from '../engine/handFlow'
import type { SessionState } from '../engine/session'
import type { DebtLoad } from '../stakes/storage'
import type { BuyIn, SettledDebt } from '../stakes/types'
/**
 * Only meaningful while `session !== null`. `betweenHands` is a real, UI-visible pause point — no
 * hand is in progress, `session.stacks` is trustworthy, and `cashOut` is only ever legal here. A
 * hand result stays visible (`lastResult`) until the next hand actually starts, so HandLog has
 * something to render. This is deliberately NOT auto-advanced past by `submitPlayerAction` — see
 * `dealHand` below for why cash-out mid-hand would be a settlement exploit if it were.
 */
export type HandPhase = { kind: 'awaiting'; step: HandStep } | { kind: 'betweenHands'; lastResult: HandResult | null }

export interface GameState {
  debtLoad: DebtLoad
  buyIn: BuyIn | null
  session: SessionState | null
  handPhase: HandPhase | null
}

type GameAction =
  | { type: 'buyIn'; buyIn: BuyIn; session: SessionState }
  | { type: 'handPhaseChanged'; session: SessionState; handPhase: HandPhase }
  | { type: 'cashedOut'; session: SessionState }
  | { type: 'debtSettled'; debts: SettledDebt[] }
  | { type: 'debtProgressLogged'; debts: SettledDebt[] }

export const initialGameState: GameState = {
  debtLoad: { status: 'ok', debts: [] },
  buyIn: null,
  session: null,
  handPhase: null,
}

/**
 * Pure state transitions. All randomness/ids/clock reads happen in the hook, never in here.
 * `GameAction` is exhaustively handled — TS errors on a missing case instead of a silent
 * fallthrough, which is why there is no `default` branch.
 */
export const gameReducer = (state: GameState, action: GameAction): GameState => {
  switch (action.type) {
    case 'buyIn':
      return { ...state, buyIn: action.buyIn, session: action.session, handPhase: null }
    case 'handPhaseChanged':
      return { ...state, session: action.session, handPhase: action.handPhase }
    case 'cashedOut':
      return { ...state, session: action.session }
    case 'debtSettled':
      return {
        ...state,
        debtLoad: { status: 'ok', debts: action.debts },
        buyIn: null,
        session: null,
        handPhase: null,
      }
    case 'debtProgressLogged':
      return { ...state, debtLoad: { status: 'ok', debts: action.debts } }
  }
}

/** An unpaid debt (owedUnits not yet fully paid) blocks starting a new session — a hard gate. */
export const hasOutstandingDebt = (debtLoad: DebtLoad): boolean =>
  debtLoad.status === 'unreadable' || debtLoad.debts.some((d) => d.paidUnits < d.owedUnits)
