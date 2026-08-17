/**
 * Everything the director's units do each tick: enemy movement and contact,
 * their fire and spawning, projectile flight, and what happens when an enemy
 * dies.
 *
 * Imports run one way — this file reaches into `simUnit` and `simSurvivor`, and
 * neither reaches back — so the simulation graph stays acyclic.
 */

import { applyStatus, factor } from './status'
import type { Enemy, EnemyKind, EnemySpec, GameState, Survivor } from './types'
import { ARENA, CONTACT_COOLDOWN, ENEMY_SPECS, FRENZY_DAMAGE, FRENZY_SPEED } from './types'
import {
  ENEMY_PROJ_TTL, SPLIT_RADIUS, SURVIVOR_RADIUS, enemySpeed, makeEnemy,
} from './simUnit'
import { grantXp } from './simSurvivor'
import type { Vec } from './vec'
import { clamp, dist, toward } from './vec'

/** Frenzy's damage multiplier, derived from state so every damage channel agrees. */
export const frenzyDamageMul = (state: GameState): number =>
  factor(state.director.frenzyTimer, FRENZY_DAMAGE)

const detonate = (state: GameState, enemy: Enemy): void => {
  const spec = ENEMY_SPECS[enemy.kind]
  enemy.hp = 0
  if (dist(enemy.pos, state.survivor.pos) <= spec.blastRadius) {
    state.survivor.hp -= spec.blastDamage * frenzyDamageMul(state)
  }
}

/**
 * Emits `splitCount` children at fixed angular offsets. Deterministic on purpose:
 * drawing from the RNG here would shift every seeded replay downstream.
 * Loop-only — `splitCount: 0` makes this a no-op without a guard branch.
 */
const split = (state: GameState, spec: EnemySpec, pos: Vec): void => {
  for (let i = 0; i < spec.splitCount; i += 1) {
    const angle = (Math.PI * 2 * i) / spec.splitCount
    makeEnemy(state, spec.spawnKind, {
      x: clamp(pos.x + Math.cos(angle) * SPLIT_RADIUS, 10, ARENA.w - 10),
      y: clamp(pos.y + Math.sin(angle) * SPLIT_RADIUS, 10, ARENA.h - 10),
    })
  }
}

const killByShot = (state: GameState, enemy: Enemy): void => {
  const spec = ENEMY_SPECS[enemy.kind]
  state.survivor.kills += 1
  grantXp(state, spec.xp)
  if (spec.detonates) {
    detonate(state, enemy)
  }
  split(state, spec, enemy.pos)
}

type MoveFn = (e: Enemy, sv: Survivor, d: number, speed: number) => Vec

const MOVE_FNS: Record<'chase' | 'skirmish', MoveFn> = {
  chase: (e, sv, _d, speed) => toward(e.pos, sv.pos, speed),
  skirmish: (e, sv, d, speed) => {
    const spec = ENEMY_SPECS[e.kind]
    if (d > spec.keepDistance) {
      return toward(e.pos, sv.pos, speed)
    }
    if (d < spec.keepDistance * 0.65) {
      return toward(sv.pos, e.pos, speed)
    }
    return { x: 0, y: 0 }
  },
}

export const enemiesStep = (state: GameState, dt: number): void => {
  const sv = state.survivor
  const spawned: { kind: EnemyKind; pos: Vec }[] = []
  // Frenzy is read straight off director state — no import, so no new import cycle.
  const speedMul = factor(state.director.frenzyTimer, FRENZY_SPEED)
  const damageMul = frenzyDamageMul(state)
  for (const e of state.enemies) {
    const spec = ENEMY_SPECS[e.kind]
    e.hitTimer = Math.max(0, e.hitTimer - dt)
    const d = dist(e.pos, sv.pos)
    const vel = MOVE_FNS[spec.move](e, sv, d, enemySpeed(state, e.kind, speedMul))
    e.pos.x = clamp(e.pos.x + vel.x * dt, spec.radius, ARENA.w - spec.radius)
    e.pos.y = clamp(e.pos.y + vel.y * dt, spec.radius, ARENA.h - spec.radius)

    if (dist(e.pos, sv.pos) <= spec.radius + SURVIVOR_RADIUS) {
      if (spec.detonates) {
        detonate(state, e)
      } else if (e.hitTimer === 0) {
        sv.hp -= spec.contactDamage * damageMul
        // Unconditional: a 0-duration spec makes this a provable no-op, which is
        // cheaper than a guard branch under the 100 % gate.
        applyStatus(sv, spec.debuff, spec.debuffDuration)
        e.hitTimer = CONTACT_COOLDOWN
      }
    }

    if (spec.projDamage > 0) {
      e.fireTimer = Math.max(0, e.fireTimer - dt)
      if (e.fireTimer === 0 && d <= spec.fireRange) {
        const id = state.nextId
        state.nextId += 1
        state.projectiles.push({
          id,
          from: 'enemy',
          pos: { x: e.pos.x, y: e.pos.y },
          vel: toward(e.pos, sv.pos, spec.projSpeed),
          radius: 5,
          damage: spec.projDamage * damageMul,
          ttl: ENEMY_PROJ_TTL,
          debuff: spec.debuff,
          debuffDuration: spec.debuffDuration,
        })
        e.fireTimer = spec.fireCooldown
      }
    }

    if (spec.spawnEvery > 0) {
      e.spawnTimer = Math.max(0, e.spawnTimer - dt)
      if (e.spawnTimer === 0) {
        spawned.push({ kind: spec.spawnKind, pos: { x: e.pos.x, y: e.pos.y } })
        e.spawnTimer = spec.spawnEvery
      }
    }
  }
  for (const s of spawned) {
    makeEnemy(state, s.kind, s.pos)
  }
}

const findHit = (enemies: Enemy[], pos: Vec, radius: number): Enemy | null => {
  for (const e of enemies) {
    if (e.hp > 0 && dist(e.pos, pos) <= ENEMY_SPECS[e.kind].radius + radius) {
      return e
    }
  }
  return null
}

export const projectilesStep = (state: GameState, dt: number): void => {
  const sv = state.survivor
  const surviving: typeof state.projectiles = []
  for (const p of state.projectiles) {
    p.pos.x += p.vel.x * dt
    p.pos.y += p.vel.y * dt
    p.ttl -= dt
    if (p.ttl <= 0) {
      continue
    }
    if (p.from === 'survivor') {
      const hit = findHit(state.enemies, p.pos, p.radius)
      if (hit !== null) {
        hit.hp -= p.damage
        if (hit.hp <= 0) {
          killByShot(state, hit)
        }
        continue
      }
    } else if (dist(p.pos, sv.pos) <= p.radius + SURVIVOR_RADIUS) {
      sv.hp -= p.damage
      applyStatus(sv, p.debuff, p.debuffDuration)
      continue
    }
    surviving.push(p)
  }
  state.projectiles = surviving
}
