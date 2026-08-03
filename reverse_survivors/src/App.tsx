import type { ReactElement } from 'react'
import { useRef, useState } from 'react'
import { fmtTime } from './ui/format'
import { createInitialState, step } from './core/sim'
import type { HudSnapshot } from './core/snapshot'
import { snapshotOf } from './core/snapshot'
import type { DirectorAction, GameState } from './core/types'
import type { Ctx2D } from './render/draw'
import { draw } from './render/draw'
import { CanvasStage } from './ui/CanvasStage'
import { Hud } from './ui/Hud'
import { SpawnBar } from './ui/SpawnBar'
import { useGameLoop } from './ui/useGameLoop'

interface Props {
  seed?: number
  /** Test seam: mutate the freshly created state before the loop starts. */
  boot?: (state: GameState) => void
}

const createGame = (seed: number, boot: Props['boot']): GameState => {
  const state = createInitialState(seed)
  if (boot !== undefined) {
    boot(state)
  }
  return state
}

export const App = ({ seed = 20260802, boot }: Props): ReactElement => {
  const gameRef = useRef<GameState>(createGame(seed, boot))
  const [snap, setSnap] = useState<HudSnapshot>(() => snapshotOf(createGame(seed, boot)))
  const ctxRef = useRef<Ctx2D | null>(null)
  const queueRef = useRef<DirectorAction[]>([])

  useGameLoop((dt) => {
    const state = gameRef.current
    step(state, queueRef.current, dt)
    queueRef.current = []
    const ctx = ctxRef.current
    if (ctx !== null) {
      draw(ctx, state)
    }
    setSnap(snapshotOf(state))
  })

  const handleAction = (action: DirectorAction): void => {
    queueRef.current.push(action)
  }
  const handleRestart = (): void => {
    gameRef.current = createGame(Date.now() >>> 0, undefined)
    queueRef.current = []
    setSnap(snapshotOf(gameRef.current))
  }
  const handleCtx = (ctx: Ctx2D | null): void => {
    ctxRef.current = ctx
  }

  return (
    <div className="frame">
      <header className="masthead">
        <h1>Reverse Survivors</h1>
        <p className="tagline">You are the horde. The hero is the problem.</p>
        <p className="clock">{fmtTime(snap.t)} / {fmtTime(snap.duration)}</p>
      </header>
      <main className="board">
        <CanvasStage onCtx={handleCtx} />
        <Hud snap={snap} onRestart={handleRestart} />
      </main>
      <SpawnBar snap={snap} onAction={handleAction} />
    </div>
  )
}
