import { useState } from 'react'
import type { ReactElement } from 'react'
import { BettingControls } from './ui/BettingControls'
import { BuyInScreen } from './ui/BuyInScreen'
import { CashOutPanel } from './ui/CashOutPanel'
import { DebtHistoryPanel } from './ui/DebtHistoryPanel'
import { HandLog } from './ui/HandLog'
import { Table } from './ui/Table'
import { useGame } from './ui/useGame'

interface AppProps {
  /** Injected so tests can drive a scripted in-memory ledger; defaults to the real localStorage. */
  storage?: Storage
  /** Injected so tests can script a deterministic deal; defaults to a per-mount clock read. */
  seed?: number
}

export const App = ({ storage = localStorage, seed }: AppProps = {}): ReactElement => {
  // Lazy init: `Date.now()` must be read once per mount, not on every render — an inline default
  // would make the component impure and re-seed the deck on each re-render.
  const [dealSeed] = useState(() => seed ?? Date.now())
  const { state, buyIn, dealHand, submitPlayerAction, cashOut, logDebtProgress } = useGame(storage, dealSeed)
  const { debtLoad, buyIn: activeBuyIn, session, handPhase } = state

  return (
    <main className="frame">
      <header className="masthead">
        <h1>Poker Stakes</h1>
        <p>Lose the hand, pay the price — in pushups, problems or reviews.</p>
      </header>
      {session === null || activeBuyIn === null ? (
        <BuyInScreen debtLoad={debtLoad} onBuyIn={buyIn} onLogDebtProgress={logDebtProgress} />
      ) : (
        <>
          <Table session={session} handPhase={handPhase} />
          {handPhase?.kind === 'awaiting' && (
            <BettingControls betting={handPhase.step.betting} onAction={submitPlayerAction} />
          )}
          {/*
            `handPhase` is never null while a session exists — `useGame.buyIn` deals the opening
            hand as part of sitting down — so the only two states here are the awaiting/between
            pair above and below.
          */}
          {handPhase?.kind === 'betweenHands' && (
            <>
              <HandLog lastResult={handPhase.lastResult} />
              <button type="button" className="button button--primary" onClick={dealHand}>
                Deal next hand
              </button>
            </>
          )}
          <CashOutPanel session={session} buyIn={activeBuyIn} handPhase={handPhase} onCashOut={cashOut} />
        </>
      )}
      <DebtHistoryPanel debtLoad={debtLoad} onLogDebtProgress={logDebtProgress} />
    </main>
  )
}
