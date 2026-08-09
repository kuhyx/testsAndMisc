import type { ReactElement } from 'react'
import type { HudSnapshot } from '../core/snapshot'
import { fmtTime } from './format'

const PHIALS: readonly number[] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

const UPGRADE_LABELS: Record<HudSnapshot['upgrades'][number]['id'], string> = {
  damage: 'sharper bolts',
  fireRate: 'faster casting',
  speed: 'fleeter feet',
  vitality: 'thicker blood',
  regen: 'knitting flesh',
  multishot: 'split volley',
}

interface Props {
  snap: HudSnapshot
  onRestart: () => void
}

export const Hud = ({ snap, onRestart }: Props): ReactElement => {
  const filled = Math.floor((snap.energy / snap.energyCap) * PHIALS.length)
  const hpPct = (snap.survivorHp / snap.survivorMaxHp) * 100
  return (
    <aside className="hud">
      <div className="hud-block">
        <h2 className="hud-label">Soul reserve</h2>
        <div className="phials" role="meter" aria-valuenow={Math.floor(snap.energy)} aria-valuemin={0} aria-valuemax={snap.energyCap}>
          {PHIALS.map((n) => (
            <span key={`phial-${String(n)}`} className={n <= filled ? 'phial phial-full' : 'phial'} />
          ))}
        </div>
        <p className="hud-num">{Math.floor(snap.energy)} / {snap.energyCap}</p>
      </div>

      <div className="hud-block">
        <h2 className="hud-label">The intruder</h2>
        <div className="hpbar">
          <div className="hpbar-fill" style={{ width: `${String(hpPct)}%` }} />
        </div>
        <p className="hud-num">
          {Math.ceil(snap.survivorHp)} hp · level {snap.survivorLevel} · {snap.kills} of yours slain
        </p>
        <ul className="status-chips">
          {snap.statuses.map((c) => (
            <li key={`st-${c.kind}`} className={`chip chip-${c.kind}`}>
              {c.label} {c.seconds}s
            </li>
          ))}
        </ul>
        <ul className="feed">
          {snap.upgrades.map((u) => (
            <li key={`up-${String(u.n)}`}>{UPGRADE_LABELS[u.id]}</li>
          ))}
        </ul>
      </div>

      {snap.frenzyActive && (
        <p className="frenzy-banner">The horde is frenzied</p>
      )}

      {snap.status === 'directorWon' && (
        <div className="overlay overlay-win">
          <h2>The intruder falls</h2>
          <p>Extinguished at {fmtTime(snap.outcomeTime)}.</p>
          <button type="button" onClick={onRestart}>Open the gates again</button>
        </div>
      )}
      {snap.status === 'survivorWon' && (
        <div className="overlay overlay-loss">
          <h2>Dawn breaks</h2>
          <p>The intruder outlasted your horde for {fmtTime(snap.duration)}.</p>
          <button type="button" onClick={onRestart}>Raise a new horde</button>
        </div>
      )}
    </aside>
  )
}
