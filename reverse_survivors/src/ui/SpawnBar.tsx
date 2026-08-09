import type { ReactElement } from 'react'
import type { BossButton, PowerButton } from '../core/snapshot'
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

const powerCaption = (p: PowerButton): string =>
  p.ready ? `${String(p.cost)} souls` : `recovering ${String(p.cooldown)}s`

export const SpawnBar = ({ snap, onAction }: Props): ReactElement => {
  const running = snap.status === 'running'
  const { ambush, frenzy, rift } = snap.powers
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
      <button
        type="button"
        className="card card-power"
        disabled={!running || !ambush.ready || !ambush.affordable}
        onClick={() => { onAction({ type: 'ambush', kind: snap.ambushKind }) }}
      >
        <span className="card-name">Ambush</span>
        <span className="card-cost">{powerCaption(ambush)}</span>
      </button>
      <button
        type="button"
        className="card card-power"
        disabled={!running || !frenzy.ready || !frenzy.affordable}
        onClick={() => { onAction({ type: 'frenzy' }) }}
      >
        <span className="card-name">Frenzy</span>
        <span className="card-cost">{powerCaption(frenzy)}</span>
      </button>
      {snap.edges.map((e) => (
        <button
          key={`edge-${String(e.edge)}`}
          type="button"
          className={e.active ? 'card card-rift card-rift-active' : 'card card-rift'}
          disabled={!running || !rift.ready || !rift.affordable}
          onClick={() => { onAction({ type: 'rift', edge: e.edge }) }}
        >
          <span className="card-name">{e.name}</span>
          <span className="card-cost">{e.active ? `open ${String(snap.riftSeconds)}s` : 'rift'}</span>
        </button>
      ))}
    </nav>
  )
}
