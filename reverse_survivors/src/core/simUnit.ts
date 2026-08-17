/**
 * Shared unit vocabulary: arena geometry, the survivor's own dimensions, and
 * enemy construction.
 *
 * This module deliberately imports nothing else from `core/` bar types and
 * vectors. Everything the per-actor step modules need in common lands here, so
 * the simulation's import graph stays a tree rather than the cycle it would be
 * if these lived beside their callers.
 */

import type { Enemy, GameState } from './types'
import type { EnemyKind } from './enemies'
import { ARENA } from './types'
import { ENEMY_SPECS } from './enemies'
import type { Vec } from './vec'

export const SURVIVOR_RADIUS = 12
export const DANGER_RADIUS = 140
export const FIRE_RANGE = 260
export const PROJ_SPEED = 420
export const PROJ_TTL = 1.5
export const ENEMY_PROJ_TTL = 2
export const SPLIT_RADIUS = 22
export const CENTER: Vec = { x: ARENA.w / 2, y: ARENA.h / 2 }

/** Single place enemy speed is derived: difficulty and frenzy both land here. */
export const enemySpeed = (state: GameState, kind: EnemyKind, frenzyMul: number): number =>
  ENEMY_SPECS[kind].speed * state.difficulty.enemySpeed * frenzyMul

export const makeEnemy = (state: GameState, kind: EnemyKind, pos: Vec): Enemy => {
  const id = state.nextId
  state.nextId += 1
  const enemy: Enemy = {
    id,
    kind,
    pos: { x: pos.x, y: pos.y },
    hp: ENEMY_SPECS[kind].hp * state.difficulty.enemyHp,
    hitTimer: 0,
    fireTimer: 0,
    spawnTimer: ENEMY_SPECS[kind].spawnEvery,
  }
  state.enemies.push(enemy)
  return enemy
}
