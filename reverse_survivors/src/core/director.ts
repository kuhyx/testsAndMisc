import { makeEnemy } from './sim'
import { nextFloat, pick } from './rng'
import type { BossKind, DirectorAction, GameState, UnitKind } from './types'
import {
  ARENA, BOSS_COOLDOWN, BOSS_ORDER, BOSS_UNLOCK_AT, ENERGY_CAP, ENEMY_SPECS,
} from './types'
import type { Vec } from './vec'
import { clamp } from './vec'

/** Energy per second: ramps every 30 seconds so pressure always grows. */
export const regenRate = (t: number): number => 6 + 2 * Math.floor(t / 30)

export const waveCost = (waveIndex: number): number => 60 + 25 * waveIndex

export const tickDirector = (state: GameState, dt: number): void => {
  const d = state.director
  d.energy = Math.min(ENERGY_CAP, d.energy + regenRate(state.t) * dt)
  for (const boss of BOSS_ORDER) {
    d.bossCooldowns[boss] = Math.max(0, d.bossCooldowns[boss] - dt)
  }
}

type EdgeFn = (roll: number) => Vec
const EDGES: readonly [EdgeFn, ...EdgeFn[]] = [
  (roll): Vec => ({ x: roll * ARENA.w, y: 0 }),
  (roll): Vec => ({ x: roll * ARENA.w, y: ARENA.h }),
  (roll): Vec => ({ x: 0, y: roll * ARENA.h }),
  (roll): Vec => ({ x: ARENA.w, y: roll * ARENA.h }),
]

export const edgeSpawnPos = (state: GameState): Vec => {
  const edge = pick(state.rng, EDGES)
  return edge(nextFloat(state.rng))
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

/** Applies a director order. Returns false when rejected (cost, lock, or cooldown). */
export const applyAction = (state: GameState, action: DirectorAction): boolean => {
  switch (action.type) {
    case 'spawn':
      return spawnUnit(state, action.kind)
    case 'wave':
      return callWave(state)
    case 'boss':
      return summonBoss(state, action.kind)
  }
}
