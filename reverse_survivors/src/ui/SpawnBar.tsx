import type { ReactElement } from 'react'
import type { BossButton } from '../core/snapshot'
import type { HudSnapshot } from '../core/snapshot'
import type { DirectorAction } from '../core/types'

interface Props {
  snap: HudSnapshot
  onAction: (action: DirectorAction) => void
}

const bossCaption = (b: BossButton): string => {
  if (b.phase === 'locked') {
    return `seals break in ${String(b.unlockIn)}s`
  }
  if (b.phase === 'cooling') {
    return `recovering ${String(b.cooldown)}s`
  }
  return `${String(b.cost)} souls`
}

export const SpawnBar = ({ snap, onAction }: Props): ReactElement => {
  const running = snap.status === 'running'
  return (
    <nav className="spawnbar" aria-label="Summoning">
      {snap.units.map((u) => (
        <button
          key={u.kind}
          type="button"
          className="card"
          disabled={!running || !u.affordable}
          onClick={() => { onAction({ type: 'spawn', kind: u.kind }) }}
        >
          <span className="card-name">{u.name}</span>
          <span className="card-cost">{u.cost} souls</span>
        </button>
      ))}
      <button
        type="button"
        className="card card-wave"
        disabled={!running || !snap.waveAffordable}
        onClick={() => { onAction({ type: 'wave' }) }}
      >
        <span className="card-name">Wave {snap.waveIndex + 1}</span>
        <span className="card-cost">{snap.waveCost} souls</span>
      </button>
      {snap.bosses.map((b) => (
        <button
          key={b.kind}
          type="button"
          className="card card-boss"
          disabled={!running || b.phase !== 'ready' || !b.affordable}
          onClick={() => { onAction({ type: 'boss', kind: b.kind }) }}
        >
          <span className="card-name">{b.name}</span>
          <span className="card-cost">{bossCaption(b)}</span>
        </button>
      ))}
    </nav>
  )
}
