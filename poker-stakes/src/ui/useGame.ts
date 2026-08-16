import { useCallback, useReducer, useRef } from 'react'
import type { Action as PokerAction } from '../engine/bettingRound'
import type { InteractiveHand } from '../engine/interactiveHand'
import { startInteractiveHand } from '../engine/interactiveHand'
import { createRng } from '../engine/rng'
import type { Rng } from '../engine/rng'
import { applyHandResult, cashOutSession, deriveBlindSize, startSession } from '../engine/session'
import type { SessionState } from '../engine/session'
import { settleSession } from '../stakes/settlement'
import { loadDebts, saveDebts } from '../stakes/storage'
import type { DebtLoad } from '../stakes/storage'
import type { BuyIn, SettledDebt } from '../stakes/types'

/** XORed into the deal seed for the opponent's independent policy RNG, per the spec's seam. */
const POLICY_SEED_SALT = 0x9e3779b9

const OPPONENT_ITERATIONS = 200
import { gameReducer, hasOutstandingDebt, initialGameState } from './gameState'
import type { GameState } from './gameState'

export type { GameState, HandPhase } from './gameState'
export { gameReducer, hasOutstandingDebt } from './gameState'

export interface UseGameResult {
  state: GameState
  buyIn: (buyIn: BuyIn) => void
  dealHand: () => void
  submitPlayerAction: (action: PokerAction) => void
  cashOut: () => void
  logDebtProgress: (debtId: string, units: number) => void
}

/** Computed once via lazy init on both `useReducer` and `useRef` below — pure given `storage`. */
const readInitialDebts = (debtLoad: DebtLoad): SettledDebt[] => (debtLoad.status === 'ok' ? debtLoad.debts : [])

export const useGame = (storage: Storage, dealSeed: number): UseGameResult => {
  const [state, dispatch] = useReducer(gameReducer, initialGameState, (): GameState => ({
    ...initialGameState,
    debtLoad: loadDebts(storage),
  }))

  const handRef = useRef<InteractiveHand | null>(null)
  const dealRngRef = useRef<Rng>(createRng(dealSeed))
  const policyRngRef = useRef<Rng>(createRng(dealSeed ^ POLICY_SEED_SALT))
  const sessionRef = useRef<SessionState | null>(null)
  const buyInRef = useRef<BuyIn | null>(null)
  // Authoritative debt list, independent of render state, so an unreadable-storage snapshot in
  // `state.debtLoad` can never cause a settle to silently drop existing debts (fail-open bug).
  // `useRef`'s initial-value argument is evaluated on every render (only the first is kept), so
  // this and `storageUnreadableRef` below both see the same `loadDebts(storage)` read `state`'s
  // own lazy initializer used — no separate read, no risk of the two disagreeing.
  const debtsRef = useRef<SettledDebt[]>(readInitialDebts(loadDebts(storage)))
  // Sticky: unreadable at load blocks buyIn for the lifetime of this hook instance, even though
  // `debtsRef` itself only ever holds `SettledDebt[]` (never a nullable/unreadable marker) — this
  // is what lets `buyIn`'s gate see 'unreadable' without a helper that collapses it to `[]` first
  // (the exact bug this session's review caught: silently unblocking the gate).
  const storageUnreadableRef = useRef<boolean>(loadDebts(storage).status !== 'ok')

  const persistDebts = useCallback(
    (debts: SettledDebt[]): SettledDebt[] => {
      debtsRef.current = debts
      saveDebts(storage, debts)
      return debts
    },
    [storage],
  )

  const settleAndPersist = useCallback(
    // Caller (dealHand / cashOut) guarantees `session.outcome` is non-null and `buyInSnapshot` is
    // the live buy-in; not re-guarded here.
    (session: SessionState & { outcome: NonNullable<SessionState['outcome']> }, buyInSnapshot: BuyIn): void => {
      const debt = settleSession(buyInSnapshot, session.outcome, crypto.randomUUID(), Date.now())
      const nextDebts = persistDebts([...debtsRef.current, debt])
      handRef.current = null
      buyInRef.current = null
      sessionRef.current = null
      dispatch({ type: 'debtSettled', debts: nextDebts })
    },
    [persistDebts],
  )

  /**
   * Deals one hand. In the rare case a seat is already all-in from posting a blind (stack ≤
   * blind size), the hand can complete with ZERO player decision points — `startInteractiveHand`
   * resolves every opponent turn internally and returns already `complete`. That result is folded
   * into the session immediately (not left for a UI round-trip that would never come), and either
   * settles the session or lands in `betweenHands` so the caller can deal again.
   */
  const dealHand = useCallback((): void => {
    const session = sessionRef.current
    const buyInSnapshot = buyInRef.current
    // Reachable only if called with no live session (before any buy-in, or after settlement) —
    // the UI only exposes this action while `handPhase.kind === 'betweenHands'`.
    if (session === null || buyInSnapshot === null) {
      return
    }
    const { bigBlind, smallBlind } = deriveBlindSize(buyInSnapshot.chips)
    const hand = startInteractiveHand(
      dealRngRef.current,
      policyRngRef.current,
      { buttonSeat: session.buttonSeat, bigBlind, smallBlind, stacks: session.stacks },
      OPPONENT_ITERATIONS,
    )
    const status = hand.status
    if (status.kind === 'awaiting') {
      handRef.current = hand
      dispatch({ type: 'handPhaseChanged', session, handPhase: { kind: 'awaiting', step: status.step } })
      return
    }
    const nextSession = applyHandResult(session, status.result)
    sessionRef.current = nextSession
    if (nextSession.outcome !== null) {
      settleAndPersist({ ...nextSession, outcome: nextSession.outcome }, buyInSnapshot)
      return
    }
    dispatch({
      type: 'handPhaseChanged',
      session: nextSession,
      handPhase: { kind: 'betweenHands', lastResult: status.result },
    })
  }, [settleAndPersist])

  const buyIn = useCallback(
    (nextBuyIn: BuyIn): void => {
      // Hard gate: an outstanding debt blocks starting a new session, per the confirmed stakes
      // model — never just a UI-level warning. Chips are integers throughout (per the plan), so a
      // non-positive or fractional buy-in is rejected here too, not just via an input `min`/`step`.
      if (
        storageUnreadableRef.current ||
        hasOutstandingDebt({ status: 'ok', debts: debtsRef.current }) ||
        !Number.isInteger(nextBuyIn.chips) ||
        nextBuyIn.chips <= 0
      ) {
        return
      }
      const session = startSession({ buyInChips: nextBuyIn.chips })
      buyInRef.current = nextBuyIn
      sessionRef.current = session
      dispatch({ type: 'buyIn', buyIn: nextBuyIn, session })
      dealHand()
    },
    [dealHand],
  )

  const submitPlayerAction = useCallback(
    (action: PokerAction): void => {
      const hand = handRef.current
      const session = sessionRef.current
      const buyInSnapshot = buyInRef.current
      // Reachable only via a submit before any buy-in — `hand.submit` itself throws if no
      // decision is pending, which per this session's review is otherwise unreachable: `dealHand`
      // never leaves `handRef` holding an already-`complete` hand.
      if (hand === null || session === null || buyInSnapshot === null) {
        return
      }
      hand.submit(action)
      const status = hand.status
      if (status.kind === 'awaiting') {
        dispatch({ type: 'handPhaseChanged', session, handPhase: { kind: 'awaiting', step: status.step } })
        return
      }
      // Hand resolved. Land in `betweenHands` — do NOT auto-deal the next hand: `session.stacks`
      // must reflect a just-completed hand so `cashOut` (only legal in `betweenHands`) settles
      // against real chips, and mid-hand cash-out would let a player see a bad flop, cash out at
      // the PRE-hand stack, and have the posted blinds/bets vanish with the discarded generator.
      handRef.current = null
      const nextSession = applyHandResult(session, status.result)
      sessionRef.current = nextSession
      if (nextSession.outcome !== null) {
        settleAndPersist({ ...nextSession, outcome: nextSession.outcome }, buyInSnapshot)
        return
      }
      dispatch({
        type: 'handPhaseChanged',
        session: nextSession,
        handPhase: { kind: 'betweenHands', lastResult: status.result },
      })
    },
    [settleAndPersist],
  )

  const cashOut = useCallback((): void => {
    const session = sessionRef.current
    const buyInSnapshot = buyInRef.current
    // Only legal between hands: `handRef.current !== null` means a hand is in progress, and
    // mid-hand `session.stacks` predates that hand's blinds/bets — cashing out then would settle
    // against a stale stack and let a player see the deal before deciding to cash out. handRef is
    // read (a synchronous ref) rather than `state.handPhase` (React state) because this guard is
    // security-critical: it must reflect what actually happened, not what has rendered yet.
    if (session?.outcome !== null || buyInSnapshot === null || handRef.current !== null) {
      return
    }
    const nextSession = cashOutSession(session)
    sessionRef.current = nextSession
    dispatch({ type: 'cashedOut', session: nextSession })
    // cashOutSession always sets outcome, so this cast just restates that fact for the type.
    settleAndPersist(nextSession as SessionState & { outcome: NonNullable<SessionState['outcome']> }, buyInSnapshot)
  }, [settleAndPersist])

  const logDebtProgress = useCallback(
    (debtId: string, units: number): void => {
      const nextDebts = debtsRef.current.map((d) =>
        d.id === debtId ? { ...d, paidUnits: Math.min(d.owedUnits, d.paidUnits + units) } : d,
      )
      persistDebts(nextDebts)
      dispatch({ type: 'debtProgressLogged', debts: nextDebts })
    },
    [persistDebts],
  )

  return { state, buyIn, dealHand, submitPlayerAction, cashOut, logDebtProgress }
}
