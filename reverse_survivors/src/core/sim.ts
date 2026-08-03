import { applyAction, tickDirector } from './director'
import { createRng, pick } from './rng'
import type {
  DirectorAction, Enemy, EnemyKind, GameState, Survivor, UpgradeId,
} from './types'
import {
  ARENA, CONTACT_COOLDOWN, ENERGY_START, ENEMY_SPECS, GAME_DURATION, UPGRADE_POOL,
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

const createSurvivor = (): Survivor => ({
  pos: { x: CENTER.x, y: CENTER.y },
  hp: 100,
  maxHp: 100,
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
})

export const createInitialState = (seed: number, duration = GAME_DURATION): GameState => ({
  status: 'running',
  t: 0,
  duration,
  rng: createRng(seed),
  survivor: createSurvivor(),
  enemies: [],
  projectiles: [],
  director: {
    energy: ENERGY_START,
    waveIndex: 0,
    bossCooldowns: { colossus: 0, hivemind: 0 },
  },
  upgrades: [],
  nextId: 1,
  outcomeTime: 0,
})

export const makeEnemy = (state: GameState, kind: EnemyKind, pos: Vec): Enemy => {
  const id = state.nextId
  state.nextId += 1
  const enemy: Enemy = {
    id,
    kind,
    pos: { x: pos.x, y: pos.y },
    hp: ENEMY_SPECS[kind].hp,
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
    vel = { x: (fleeX / fleeMag) * sv.speed, y: (fleeY / fleeMag) * sv.speed }
  } else if (dist(sv.pos, CENTER) > 4) {
    vel = toward(sv.pos, CENTER, sv.speed * 0.4)
  }
  sv.pos.x = clamp(sv.pos.x + vel.x * dt, SURVIVOR_RADIUS, ARENA.w - SURVIVOR_RADIUS)
  sv.pos.y = clamp(sv.pos.y + vel.y * dt, SURVIVOR_RADIUS, ARENA.h - SURVIVOR_RADIUS)

  sv.hp = Math.min(sv.maxHp, sv.hp + sv.regen * dt)

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
      })
    }
    sv.fireTimer = sv.fireCooldown
  }
}

const detonate = (state: GameState, enemy: Enemy): void => {
  const spec = ENEMY_SPECS[enemy.kind]
  enemy.hp = 0
  if (dist(enemy.pos, state.survivor.pos) <= spec.blastRadius) {
    state.survivor.hp -= spec.blastDamage
  }
}

const killByShot = (state: GameState, enemy: Enemy): void => {
  const spec = ENEMY_SPECS[enemy.kind]
  state.survivor.kills += 1
  grantXp(state, spec.xp)
  if (spec.detonates) {
    detonate(state, enemy)
  }
}

const MOVE_FNS: Record<'chase' | 'skirmish', (e: Enemy, sv: Survivor, d: number) => Vec> = {
  chase: (e, sv) => toward(e.pos, sv.pos, ENEMY_SPECS[e.kind].speed),
  skirmish: (e, sv, d) => {
    const spec = ENEMY_SPECS[e.kind]
    if (d > spec.keepDistance) {
      return toward(e.pos, sv.pos, spec.speed)
    }
    if (d < spec.keepDistance * 0.65) {
      return toward(sv.pos, e.pos, spec.speed)
    }
    return { x: 0, y: 0 }
  },
}

const enemiesStep = (state: GameState, dt: number): void => {
  const sv = state.survivor
  const spawned: { kind: EnemyKind; pos: Vec }[] = []
  for (const e of state.enemies) {
    const spec = ENEMY_SPECS[e.kind]
    e.hitTimer = Math.max(0, e.hitTimer - dt)
    const d = dist(e.pos, sv.pos)
    const vel = MOVE_FNS[spec.move](e, sv, d)
    e.pos.x = clamp(e.pos.x + vel.x * dt, spec.radius, ARENA.w - spec.radius)
    e.pos.y = clamp(e.pos.y + vel.y * dt, spec.radius, ARENA.h - spec.radius)

    if (dist(e.pos, sv.pos) <= spec.radius + SURVIVOR_RADIUS) {
      if (spec.detonates) {
        detonate(state, e)
      } else if (e.hitTimer === 0) {
        sv.hp -= spec.contactDamage
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
          damage: spec.projDamage,
          ttl: ENEMY_PROJ_TTL,
        })
        e.fireTimer = spec.fireCooldown
      }
    }

    if (spec.spawnEvery > 0) {
      e.spawnTimer = Math.max(0, e.spawnTimer - dt)
      if (e.spawnTimer === 0) {
        spawned.push({ kind: 'rusher', pos: { x: e.pos.x, y: e.pos.y } })
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
