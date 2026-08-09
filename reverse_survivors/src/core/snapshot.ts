import { waveCost } from './director'
import type { BossKind, GameState, Status, StatusKind, UnitKind, UpgradeId } from './types'
import {
  BOSS_ORDER, BOSS_UNLOCK_AT, ENERGY_CAP, ENEMY_SPECS, STATUS_LABELS, STATUS_ORDER, UNIT_ORDER,
} from './types'

export type BossPhase = 'locked' | 'cooling' | 'ready'

export interface UnitButton {
  kind: UnitKind
  name: string
  cost: number
  affordable: boolean
}

export interface BossButton {
  kind: BossKind
  name: string
  cost: number
  phase: BossPhase
  unlockIn: number
  cooldown: number
  affordable: boolean
}

export interface UpgradeEntry {
  n: number
  id: UpgradeId
}

export interface StatusChip {
  kind: StatusKind
  label: string
  seconds: number
}

export interface HudSnapshot {
  status: Status
  t: number
  duration: number
  energy: number
  energyCap: number
  waveIndex: number
  waveCost: number
  waveAffordable: boolean
  survivorHp: number
  survivorMaxHp: number
  survivorLevel: number
  kills: number
  upgrades: UpgradeEntry[]
  units: UnitButton[]
  bosses: BossButton[]
  statuses: StatusChip[]
  outcomeTime: number
}

const bossPhase = (state: GameState, kind: BossKind): BossPhase => {
  if (state.t < BOSS_UNLOCK_AT[kind]) {
    return 'locked'
  }
  if (state.director.bossCooldowns[kind] > 0) {
    return 'cooling'
  }
  return 'ready'
}

export const snapshotOf = (state: GameState): HudSnapshot => ({
  status: state.status,
  t: state.t,
  duration: state.duration,
  energy: state.director.energy,
  energyCap: ENERGY_CAP,
  waveIndex: state.director.waveIndex,
  waveCost: waveCost(state.director.waveIndex),
  waveAffordable: state.director.energy >= waveCost(state.director.waveIndex),
  survivorHp: Math.max(0, state.survivor.hp),
  survivorMaxHp: state.survivor.maxHp,
  survivorLevel: state.survivor.level,
  kills: state.survivor.kills,
  upgrades: state.upgrades.map((id, i) => ({ n: i + 1, id })).slice(-3),
  statuses: STATUS_ORDER
    .map((kind) => ({
      kind,
      label: STATUS_LABELS[kind],
      seconds: Math.ceil(state.survivor.statuses[kind]),
    }))
    .filter((chip) => chip.seconds > 0),
  units: UNIT_ORDER.map((kind) => ({
    kind,
    name: ENEMY_SPECS[kind].name,
    cost: ENEMY_SPECS[kind].cost,
    affordable: state.director.energy >= ENEMY_SPECS[kind].cost,
  })),
  bosses: BOSS_ORDER.map((kind) => ({
    kind,
    name: ENEMY_SPECS[kind].name,
    cost: ENEMY_SPECS[kind].cost,
    phase: bossPhase(state, kind),
    unlockIn: Math.max(0, Math.ceil(BOSS_UNLOCK_AT[kind] - state.t)),
    cooldown: Math.ceil(state.director.bossCooldowns[kind]),
    affordable: state.director.energy >= ENEMY_SPECS[kind].cost,
  })),
  outcomeTime: state.outcomeTime,
})
