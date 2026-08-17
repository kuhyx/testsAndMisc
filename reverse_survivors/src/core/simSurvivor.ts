/**
 * The survivor: how one is created, how it levels, and what it does each tick.
 *
 * The survivor is the *opponent* in this game — it is driven entirely by this
 * file rather than by input. Its behaviour is a flee-from-crowds vector with a
 * drift back to the arena centre, plus auto-fire at the nearest target in range.
 */

import { pick } from './rng'
import { factor, tickStatuses } from './status'
import type { DifficultyConfig, Enemy, GameState, Survivor, UpgradeId } from './types'
import { ARENA, STATUS_POWER, UPGRADE_POOL } from './types'
import {
  CENTER, DANGER_RADIUS, FIRE_RANGE, PROJ_SPEED, PROJ_TTL, SURVIVOR_RADIUS,
} from './simUnit'
import type { Vec } from './vec'
import { clamp, dist, toward } from './vec'

export const xpForLevel = (level: number): number => 20 + 15 * (level - 1)

export const createSurvivor = (cfg: DifficultyConfig): Survivor => ({
  pos: { x: CENTER.x, y: CENTER.y },
  hp: 100 * cfg.survivorHp,
  maxHp: 100 * cfg.survivorHp,
  speed: 150,
  regen: 0,
  damage: 8,
  multishot: 1,
  fireCooldown: 0.55,
  fireTimer: 0,
  level: 1,
  xp: 0,
  xpNext: xpForLevel(1),
  kills: 0,
  statuses: { slow: 0, suppress: 0, bleed: 0 },
})

const APPLY_UPGRADE: Record<UpgradeId, (sv: Survivor) => void> = {
  damage: (sv) => { sv.damage += 3 },
  fireRate: (sv) => { sv.fireCooldown = Math.max(0.15, sv.fireCooldown * 0.88) },
  speed: (sv) => { sv.speed += 14 },
  vitality: (sv) => { sv.maxHp += 20; sv.hp += 20 },
  regen: (sv) => { sv.regen += 0.6 },
  multishot: (sv) => { sv.multishot += 1 },
}

export const applyUpgrade = (sv: Survivor, id: UpgradeId): void => {
  APPLY_UPGRADE[id](sv)
}

export const grantXp = (state: GameState, amount: number): void => {
  const sv = state.survivor
  sv.xp += amount
  while (sv.xp >= sv.xpNext) {
    sv.xp -= sv.xpNext
    sv.level += 1
    sv.xpNext = xpForLevel(sv.level)
    const upgrade = pick(state.rng, UPGRADE_POOL)
    applyUpgrade(sv, upgrade)
    state.upgrades.push(upgrade)
  }
}

const nearestEnemy = (state: GameState): Enemy | null => {
  let best: Enemy | null = null
  let bestD = Infinity
  for (const e of state.enemies) {
    const d = dist(e.pos, state.survivor.pos)
    if (d < bestD) {
      bestD = d
      best = e
    }
  }
  return best
}

export const survivorStep = (state: GameState, dt: number): void => {
  const sv = state.survivor
  // Tick before reading: a status applied this tick is felt from the next one,
  // and a 0-second (inert) application is never observable.
  tickStatuses(sv, dt)
  const moveMul = factor(sv.statuses.slow, STATUS_POWER.slow)
  const fireMul = factor(sv.statuses.suppress, STATUS_POWER.suppress)
  const regenMul = factor(sv.statuses.bleed, STATUS_POWER.bleed)
  const speed = sv.speed * moveMul
  let fleeX = 0
  let fleeY = 0
  for (const e of state.enemies) {
    const d = dist(e.pos, sv.pos)
    if (d < DANGER_RADIUS && d > 0) {
      const weight = (DANGER_RADIUS - d) / DANGER_RADIUS
      fleeX += ((sv.pos.x - e.pos.x) / d) * weight
      fleeY += ((sv.pos.y - e.pos.y) / d) * weight
    }
  }
  const fleeMag = Math.hypot(fleeX, fleeY)
  let vel: Vec = { x: 0, y: 0 }
  if (fleeMag > 0) {
    vel = { x: (fleeX / fleeMag) * speed, y: (fleeY / fleeMag) * speed }
  } else if (dist(sv.pos, CENTER) > 4) {
    vel = toward(sv.pos, CENTER, speed * 0.4)
  }
  sv.pos.x = clamp(sv.pos.x + vel.x * dt, SURVIVOR_RADIUS, ARENA.w - SURVIVOR_RADIUS)
  sv.pos.y = clamp(sv.pos.y + vel.y * dt, SURVIVOR_RADIUS, ARENA.h - SURVIVOR_RADIUS)

  sv.hp = Math.min(sv.maxHp, sv.hp + sv.regen * regenMul * dt)

  sv.fireTimer = Math.max(0, sv.fireTimer - dt)
  const target = nearestEnemy(state)
  if (target !== null && sv.fireTimer === 0 && dist(target.pos, sv.pos) <= FIRE_RANGE) {
    const baseAngle = Math.atan2(target.pos.y - sv.pos.y, target.pos.x - sv.pos.x)
    for (let i = 0; i < sv.multishot; i += 1) {
      const angle = baseAngle + (i - (sv.multishot - 1) / 2) * 0.12
      const id = state.nextId
      state.nextId += 1
      state.projectiles.push({
        id,
        from: 'survivor',
        pos: { x: sv.pos.x, y: sv.pos.y },
        vel: { x: Math.cos(angle) * PROJ_SPEED, y: Math.sin(angle) * PROJ_SPEED },
        radius: 4,
        damage: sv.damage,
        ttl: PROJ_TTL,
        debuff: 'slow',
        debuffDuration: 0,
      })
    }
    // Suppression scales the reload, not the countdown: the remaining timer stays
    // linear in dt, which keeps replays and assertions exact.
    sv.fireTimer = sv.fireCooldown * fireMul
  }
}
