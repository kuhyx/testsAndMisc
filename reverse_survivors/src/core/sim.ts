import { applyAction, tickDirector } from './director'
import { createRng, pick } from './rng'
import { applyStatus, factor, tickStatuses } from './status'
import type {
  DifficultyConfig, DifficultyId, DirectorAction, Enemy, EnemyKind, EnemySpec, GameState,
  Survivor, UpgradeId,
} from './types'
import {
  ARENA, CONTACT_COOLDOWN, DIFFICULTIES, ENERGY_START, ENEMY_SPECS, FRENZY_DAMAGE,
  FRENZY_SPEED, STATUS_POWER, UPGRADE_POOL,
} from './types'
import type { Vec } from './vec'
import { clamp, dist, toward } from './vec'

export const SURVIVOR_RADIUS = 12
export const DANGER_RADIUS = 140
export const FIRE_RANGE = 260
export const PROJ_SPEED = 420
const PROJ_TTL = 1.5
const ENEMY_PROJ_TTL = 2
const CENTER: Vec = { x: ARENA.w / 2, y: ARENA.h / 2 }

export const xpForLevel = (level: number): number => 20 + 15 * (level - 1)

const createSurvivor = (cfg: DifficultyConfig): Survivor => ({
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

export const createInitialState = (
  seed: number,
  duration?: number,
  difficulty: DifficultyId = 'normal',
): GameState => {
  const cfg = DIFFICULTIES[difficulty]
  return {
    status: 'running',
    difficulty: cfg,
    t: 0,
    duration: duration ?? cfg.duration,
    rng: createRng(seed),
    survivor: createSurvivor(cfg),
    enemies: [],
    projectiles: [],
    director: {
      energy: ENERGY_START,
      waveIndex: 0,
      bossCooldowns: { colossus: 0, hivemind: 0, leech: 0 },
      powerCooldowns: { ambush: 0, frenzy: 0, rift: 0 },
      frenzyTimer: 0,
      riftTimer: 0,
      riftEdge: 0,
      ambushIndex: 0,
    },
    upgrades: [],
    nextId: 1,
    outcomeTime: 0,
  }
}

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

const survivorStep = (state: GameState, dt: number): void => {
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

export const SPLIT_RADIUS = 22

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

const enemiesStep = (state: GameState, dt: number): void => {
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

const projectilesStep = (state: GameState, dt: number): void => {
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

export const step = (state: GameState, actions: readonly DirectorAction[], dt: number): void => {
  if (state.status !== 'running') {
    return
  }
  state.t += dt
  tickDirector(state, dt)
  for (const action of actions) {
    applyAction(state, action)
  }
  survivorStep(state, dt)
  enemiesStep(state, dt)
  projectilesStep(state, dt)
  state.enemies = state.enemies.filter((e) => e.hp > 0)
  if (state.survivor.hp <= 0) {
    state.status = 'directorWon'
    state.outcomeTime = state.t
  } else if (state.t >= state.duration) {
    state.status = 'survivorWon'
    state.outcomeTime = state.t
  }
}
