import { makeEnemy } from './sim'
import { nextFloat, pick } from './rng'
import type { BossKind, DirectorAction, EdgeId, GameState, PowerKind, UnitKind } from './types'
import {
  AMBUSH_RADIUS, ARENA, BOSS_COOLDOWN, BOSS_ORDER, BOSS_UNLOCK_AT, EDGE_ORDER, ENERGY_CAP,
  ENEMY_SPECS, FRENZY_DURATION, GOLDEN_ANGLE, POWER_COOLDOWN, POWER_COST, POWER_ORDER,
  RIFT_DURATION,
} from './types'
import type { Vec } from './vec'
import { clamp } from './vec'

/** Energy per second: ramps every 30 seconds so pressure always grows. */
export const regenRate = (t: number, rate = 1): number => (6 + 2 * Math.floor(t / 30)) * rate

export const waveCost = (waveIndex: number): number => 60 + 25 * waveIndex

export const tickDirector = (state: GameState, dt: number): void => {
  const d = state.director
  d.energy = Math.min(ENERGY_CAP, d.energy + regenRate(state.t, state.difficulty.energyRate) * dt)
  for (const boss of BOSS_ORDER) {
    d.bossCooldowns[boss] = Math.max(0, d.bossCooldowns[boss] - dt)
  }
  for (const power of POWER_ORDER) {
    d.powerCooldowns[power] = Math.max(0, d.powerCooldowns[power] - dt)
  }
  d.frenzyTimer = Math.max(0, d.frenzyTimer - dt)
  d.riftTimer = Math.max(0, d.riftTimer - dt)
}

type EdgeFn = (roll: number) => Vec
/** Keyed by EdgeId rather than an array: index access then stays non-optional. */
const EDGES: Record<EdgeId, EdgeFn> = {
  0: (roll): Vec => ({ x: roll * ARENA.w, y: 0 }),
  1: (roll): Vec => ({ x: roll * ARENA.w, y: ARENA.h }),
  2: (roll): Vec => ({ x: 0, y: roll * ARENA.h }),
  3: (roll): Vec => ({ x: ARENA.w, y: roll * ARENA.h }),
}

/**
 * A live rift pins the edge; otherwise the RNG picks. The unpinned path draws
 * exactly two values in the original order, so existing seeded replays are unchanged.
 */
export const edgeSpawnPos = (state: GameState): Vec => {
  const d = state.director
  const chosen = d.riftTimer > 0 ? d.riftEdge : pick(state.rng, EDGE_ORDER)
  return EDGES[chosen](nextFloat(state.rng))
}

const spawnUnit = (state: GameState, kind: UnitKind): boolean => {
  const spec = ENEMY_SPECS[kind]
  if (state.director.energy < spec.cost) {
    return false
  }
  state.director.energy -= spec.cost
  makeEnemy(state, kind, edgeSpawnPos(state))
  return true
}

const callWave = (state: GameState): boolean => {
  const cost = waveCost(state.director.waveIndex)
  if (state.director.energy < cost) {
    return false
  }
  state.director.energy -= cost
  const w = state.director.waveIndex
  const rushers = 6 + 2 * w
  const stalkers = w
  const total = rushers + stalkers
  const sv = state.survivor.pos
  for (let i = 0; i < total; i += 1) {
    const angle = (Math.PI * 2 * i) / total + nextFloat(state.rng) * 0.3
    const kind = i < rushers ? 'rusher' : 'stalker'
    makeEnemy(state, kind, {
      x: clamp(sv.x + Math.cos(angle) * 280, 10, ARENA.w - 10),
      y: clamp(sv.y + Math.sin(angle) * 280, 10, ARENA.h - 10),
    })
  }
  state.director.waveIndex += 1
  return true
}

const summonBoss = (state: GameState, kind: BossKind): boolean => {
  if (state.t < BOSS_UNLOCK_AT[kind]) {
    return false
  }
  if (state.director.bossCooldowns[kind] > 0) {
    return false
  }
  const spec = ENEMY_SPECS[kind]
  if (state.director.energy < spec.cost) {
    return false
  }
  state.director.energy -= spec.cost
  makeEnemy(state, kind, edgeSpawnPos(state))
  state.director.bossCooldowns[kind] = BOSS_COOLDOWN[kind]
  return true
}

/**
 * Shared gate for every power: one cooldown check and one affordability check,
 * so adding a power costs no new branches here.
 *
 * Named `spendPower`, not `usePower`: the React hooks lint rules treat any
 * `use`-prefixed function as a hook and reject calls from plain functions.
 */
const spendPower = (state: GameState, kind: PowerKind, extra: number): boolean => {
  const d = state.director
  if (d.powerCooldowns[kind] > 0) {
    return false
  }
  const cost = POWER_COST[kind] + extra
  if (d.energy < cost) {
    return false
  }
  d.energy -= cost
  d.powerCooldowns[kind] = POWER_COOLDOWN[kind]
  return true
}

const ambush = (state: GameState, kind: UnitKind): boolean => {
  if (!spendPower(state, 'ambush', ENEMY_SPECS[kind].cost)) {
    return false
  }
  const d = state.director
  // Golden angle: an irrational fraction of a turn, so successive ambushes keep
  // landing in the widest remaining gap and never repeat a lane. (A rational
  // step like 2*PI/7 looks varied but silently cycles every 7 summons.)
  const angle = d.ambushIndex * GOLDEN_ANGLE
  d.ambushIndex += 1
  const sv = state.survivor.pos
  makeEnemy(state, kind, {
    x: clamp(sv.x + Math.cos(angle) * AMBUSH_RADIUS, 10, ARENA.w - 10),
    y: clamp(sv.y + Math.sin(angle) * AMBUSH_RADIUS, 10, ARENA.h - 10),
  })
  return true
}

const frenzy = (state: GameState): boolean => {
  if (!spendPower(state, 'frenzy', 0)) {
    return false
  }
  state.director.frenzyTimer = FRENZY_DURATION
  return true
}

const rift = (state: GameState, edge: EdgeId): boolean => {
  if (!spendPower(state, 'rift', 0)) {
    return false
  }
  state.director.riftEdge = edge
  state.director.riftTimer = RIFT_DURATION
  return true
}

/** Applies a director order. Returns false when rejected (cost, lock, or cooldown). */
export const applyAction = (state: GameState, action: DirectorAction): boolean => {
  switch (action.type) {
    case 'spawn':
      return spawnUnit(state, action.kind)
    case 'wave':
      return callWave(state)
    case 'boss':
      return summonBoss(state, action.kind)
    case 'ambush':
      return ambush(state, action.kind)
    case 'frenzy':
      return frenzy(state)
    case 'rift':
      return rift(state, action.edge)
  }
}
