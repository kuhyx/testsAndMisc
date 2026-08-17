import { waveCost } from './director'
import type { EdgeId, GameState, PowerKind, Status, UpgradeId } from './types'
import type { BossKind, UnitKind } from './enemies'
import type { StatusKind } from './statusKinds'
import { EDGE_NAMES, EDGE_ORDER, ENERGY_CAP, POWER_COST, POWER_NAMES, POWER_ORDER } from './types'
import { BOSS_ORDER, BOSS_UNLOCK_AT, ENEMY_SPECS, UNIT_ORDER } from './enemies'
import { STATUS_LABELS, STATUS_ORDER } from './statusKinds'

export type BossPhase = 'locked' | 'cooling' | 'ready'

/** Ambush summons a fixed cheap unit, so the bar needs no unit-selection mode. */
export const AMBUSH_UNIT: UnitKind = 'rusher'

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

export interface PowerButton {
  kind: PowerKind
  name: string
  cost: number
  cooldown: number
  ready: boolean
  affordable: boolean
}

export interface EdgeButton {
  edge: EdgeId
  name: string
  active: boolean
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
  powers: Record<PowerKind, PowerButton>
  edges: EdgeButton[]
  frenzyActive: boolean
  riftSeconds: number
  ambushKind: UnitKind
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

/** Ambush also pays for the unit it summons; the others carry no surcharge. */
const POWER_SURCHARGE: Record<PowerKind, number> = {
  ambush: ENEMY_SPECS[AMBUSH_UNIT].cost,
  frenzy: 0,
  rift: 0,
}

const powerButtons = (state: GameState): Record<PowerKind, PowerButton> => {
  const out = {} as Record<PowerKind, PowerButton>
  for (const kind of POWER_ORDER) {
    const cost = POWER_COST[kind] + POWER_SURCHARGE[kind]
    out[kind] = {
      kind,
      name: POWER_NAMES[kind],
      cost,
      cooldown: Math.ceil(state.director.powerCooldowns[kind]),
      ready: state.director.powerCooldowns[kind] === 0,
      affordable: state.director.energy >= cost,
    }
  }
  return out
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
  powers: powerButtons(state),
  edges: EDGE_ORDER.map((edge) => ({
    edge,
    name: EDGE_NAMES[edge],
    active: state.director.riftTimer > 0 && state.director.riftEdge === edge,
  })),
  frenzyActive: state.director.frenzyTimer > 0,
  riftSeconds: Math.ceil(state.director.riftTimer),
  ambushKind: AMBUSH_UNIT,
  outcomeTime: state.outcomeTime,
})
