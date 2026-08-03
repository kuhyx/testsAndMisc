import { describe, expect, it } from 'vitest'
import {
  applyUpgrade, createInitialState, DANGER_RADIUS, grantXp, makeEnemy, step, xpForLevel,
} from './sim'
import type { GameState, Projectile } from './types'
import { ARENA, GAME_DURATION } from './types'

const CENTER = { x: ARENA.w / 2, y: ARENA.h / 2 }

const fresh = (seed = 1, duration?: number): GameState =>
  duration === undefined ? createInitialState(seed) : createInitialState(seed, duration)

const shot = (state: GameState, x: number, y: number, damage: number): Projectile => {
  const p: Projectile = {
    id: state.nextId,
    from: 'survivor',
    pos: { x, y },
    vel: { x: 0, y: 0 },
    radius: 4,
    damage,
    ttl: 1,
  }
  state.nextId += 1
  state.projectiles.push(p)
  return p
}

describe('createInitialState', () => {
  it('uses the default duration when omitted', () => {
    expect(fresh().duration).toBe(GAME_DURATION)
  })

  it('accepts a duration override', () => {
    expect(fresh(1, 5).duration).toBe(5)
  })

  it('starts the survivor at the arena center', () => {
    expect(fresh().survivor.pos).toEqual(CENTER)
  })
})

describe('xp and upgrades', () => {
  it('thresholds grow linearly', () => {
    expect(xpForLevel(1)).toBe(20)
    expect(xpForLevel(3)).toBe(50)
  })

  it('grantXp below threshold only accumulates', () => {
    const s = fresh()
    grantXp(s, 10)
    expect(s.survivor.level).toBe(1)
    expect(s.survivor.xp).toBe(10)
    expect(s.upgrades).toHaveLength(0)
  })

  it('grantXp can jump multiple levels and logs one upgrade per level', () => {
    const s = fresh()
    grantXp(s, 60)
    expect(s.survivor.level).toBe(3)
    expect(s.survivor.xp).toBe(5)
    expect(s.upgrades).toHaveLength(2)
  })

  it('each upgrade mutates the survivor as designed', () => {
    const s = fresh().survivor
    applyUpgrade(s, 'damage')
    expect(s.damage).toBe(11)
    applyUpgrade(s, 'speed')
    expect(s.speed).toBe(164)
    applyUpgrade(s, 'vitality')
    expect(s.maxHp).toBe(120)
    expect(s.hp).toBe(120)
    applyUpgrade(s, 'regen')
    expect(s.regen).toBeCloseTo(0.6)
    applyUpgrade(s, 'multishot')
    expect(s.multishot).toBe(2)
    applyUpgrade(s, 'fireRate')
    expect(s.fireCooldown).toBeCloseTo(0.55 * 0.88)
  })

  it('fire rate floors at 0.15', () => {
    const s = fresh().survivor
    for (let i = 0; i < 30; i += 1) {
      applyUpgrade(s, 'fireRate')
    }
    expect(s.fireCooldown).toBe(0.15)
  })
})

describe('survivor movement', () => {
  it('idles when centered with no threats', () => {
    const s = fresh()
    step(s, [], 0.1)
    expect(s.survivor.pos).toEqual(CENTER)
  })

  it('seeks the center when displaced', () => {
    const s = fresh()
    s.survivor.pos = { x: 100, y: CENTER.y }
    step(s, [], 0.1)
    expect(s.survivor.pos.x).toBeGreaterThan(100)
  })

  it('flees from a close enemy', () => {
    const s = fresh()
    makeEnemy(s, 'rusher', { x: CENTER.x + 20, y: CENTER.y })
    step(s, [], 0.05)
    expect(s.survivor.pos.x).toBeLessThan(CENTER.x)
  })

  it('ignores enemies beyond the danger radius when moving', () => {
    const s = fresh()
    makeEnemy(s, 'rusher', { x: CENTER.x + DANGER_RADIUS + 60, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.survivor.pos.x).toBe(CENTER.x)
  })

  it('survives an enemy exactly on top of it without NaN positions', () => {
    const s = fresh()
    makeEnemy(s, 'rusher', { x: CENTER.x, y: CENTER.y })
    step(s, [], 0.01)
    expect(Number.isFinite(s.survivor.pos.x)).toBe(true)
    expect(Number.isFinite(s.survivor.pos.y)).toBe(true)
  })
})

describe('survivor firing', () => {
  it('does not fire with no enemies', () => {
    const s = fresh()
    step(s, [], 0.05)
    expect(s.projectiles).toHaveLength(0)
  })

  it('does not fire at enemies beyond range', () => {
    const s = fresh()
    makeEnemy(s, 'tank', { x: CENTER.x + 400, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.projectiles).toHaveLength(0)
  })

  it('fires at an enemy in range and honors the cooldown', () => {
    const s = fresh()
    makeEnemy(s, 'tank', { x: CENTER.x + 200, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.projectiles).toHaveLength(1)
    step(s, [], 0.01)
    expect(s.projectiles).toHaveLength(1)
  })

  it('aims at the nearest of several enemies', () => {
    const s = fresh()
    makeEnemy(s, 'tank', { x: CENTER.x - 280, y: CENTER.y })
    const near = makeEnemy(s, 'tank', { x: CENTER.x + 200, y: CENTER.y })
    step(s, [], 0.001)
    const p = s.projectiles[0]
    expect(p?.vel.x).toBeGreaterThan(0)
    expect(near.hp).toBe(120)
  })

  it('multishot fires a spread', () => {
    const s = fresh()
    s.survivor.multishot = 3
    makeEnemy(s, 'tank', { x: CENTER.x + 200, y: CENTER.y })
    step(s, [], 0.001)
    expect(s.projectiles).toHaveLength(3)
  })
})

describe('enemy behaviors', () => {
  it('chasers close the distance', () => {
    const s = fresh()
    const e = makeEnemy(s, 'rusher', { x: CENTER.x + 300, y: CENTER.y })
    step(s, [], 0.1)
    expect(e.pos.x).toBeLessThan(CENTER.x + 300)
  })

  it('melee contact damages the survivor once per cooldown window', () => {
    const s = fresh()
    makeEnemy(s, 'rusher', { x: CENTER.x, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.survivor.hp).toBe(100 - 6)
    step(s, [], 0.01)
    expect(s.survivor.hp).toBe(100 - 6)
  })

  it('tank hits harder', () => {
    const s = fresh()
    makeEnemy(s, 'tank', { x: CENTER.x + 5, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.survivor.hp).toBe(100 - 14)
  })

  it('stalker approaches when too far', () => {
    const s = fresh()
    const e = makeEnemy(s, 'stalker', { x: CENTER.x + 300, y: CENTER.y })
    step(s, [], 0.05)
    expect(e.pos.x).toBeLessThan(CENTER.x + 300)
  })

  it('stalker retreats when too close', () => {
    const s = fresh()
    const e = makeEnemy(s, 'stalker', { x: CENTER.x + 100, y: CENTER.y })
    step(s, [], 0.05)
    expect(e.pos.x).toBeGreaterThan(CENTER.x + 100)
  })

  it('stalker holds position inside its comfort band', () => {
    const s = fresh()
    const e = makeEnemy(s, 'stalker', { x: CENTER.x + 160, y: CENTER.y })
    const before = e.pos.x
    step(s, [], 0.05)
    expect(e.pos.x).toBe(before)
  })

  it('stalker fires when in range and ready, then cools down', () => {
    const s = fresh()
    makeEnemy(s, 'stalker', { x: CENTER.x + 220, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.projectiles.filter((p) => p.from === 'enemy')).toHaveLength(1)
    step(s, [], 0.01)
    expect(s.projectiles.filter((p) => p.from === 'enemy')).toHaveLength(1)
  })

  it('stalker does not fire from beyond its range', () => {
    const s = fresh()
    makeEnemy(s, 'stalker', { x: CENTER.x + 400, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.projectiles.filter((p) => p.from === 'enemy')).toHaveLength(0)
  })

  it('hivemind emits a rusher on its spawn cadence', () => {
    const s = fresh()
    const hive = makeEnemy(s, 'hivemind', { x: 900, y: 560 })
    step(s, [], 2.5)
    expect(s.enemies.filter((e) => e.kind === 'rusher')).toHaveLength(1)
    expect(hive.spawnTimer).toBe(2.5)
    step(s, [], 0.1)
    expect(s.enemies.filter((e) => e.kind === 'rusher')).toHaveLength(1)
  })
})

describe('bomber', () => {
  it('detonates on contact: damages the survivor, dies, grants nothing', () => {
    const s = fresh()
    makeEnemy(s, 'bomber', { x: CENTER.x, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.survivor.hp).toBe(100 - 22)
    expect(s.enemies).toHaveLength(0)
    expect(s.survivor.kills).toBe(0)
    expect(s.survivor.xp).toBe(0)
  })

  it('sniped from afar: grants xp, blast misses the survivor', () => {
    const s = fresh()
    makeEnemy(s, 'bomber', { x: CENTER.x + 300, y: CENTER.y })
    shot(s, CENTER.x + 300, CENTER.y, 99)
    step(s, [], 0.001)
    expect(s.survivor.kills).toBe(1)
    expect(s.survivor.xp).toBe(10)
    expect(s.survivor.hp).toBe(100)
    expect(s.enemies).toHaveLength(0)
  })

  it('shot inside blast range: grants xp and still burns the survivor', () => {
    const s = fresh()
    makeEnemy(s, 'bomber', { x: CENTER.x + 30, y: CENTER.y })
    shot(s, CENTER.x + 30, CENTER.y, 99)
    step(s, [], 0.001)
    expect(s.survivor.kills).toBe(1)
    expect(s.survivor.hp).toBeCloseTo(100 - 22, 5)
  })
})

describe('projectiles', () => {
  it('expire by ttl', () => {
    const s = fresh()
    shot(s, 50, 50, 1)
    step(s, [], 2)
    expect(s.projectiles).toHaveLength(0)
  })

  it('a miss keeps flying', () => {
    const s = fresh()
    shot(s, 50, 50, 1)
    step(s, [], 0.01)
    expect(s.projectiles).toHaveLength(1)
  })

  it('damages without killing when the target outlasts the hit', () => {
    const s = fresh()
    const tank = makeEnemy(s, 'tank', { x: CENTER.x + 400, y: CENTER.y })
    shot(s, CENTER.x + 400, CENTER.y, 8)
    step(s, [], 0.001)
    expect(tank.hp).toBe(112)
    expect(s.survivor.kills).toBe(0)
    expect(s.enemies).toHaveLength(1)
  })

  it('a second projectile in the same tick passes through an already-dead target', () => {
    const s = fresh()
    makeEnemy(s, 'rusher', { x: CENTER.x + 400, y: CENTER.y })
    shot(s, CENTER.x + 400, CENTER.y, 20)
    shot(s, CENTER.x + 400, CENTER.y, 20)
    step(s, [], 0.001)
    expect(s.survivor.kills).toBe(1)
    expect(s.projectiles).toHaveLength(1)
  })

  it('enemy fire hurts the survivor', () => {
    const s = fresh()
    s.projectiles.push({
      id: 500, from: 'enemy', pos: { x: CENTER.x, y: CENTER.y },
      vel: { x: 0, y: 0 }, radius: 5, damage: 7, ttl: 1,
    })
    step(s, [], 0.001)
    expect(s.survivor.hp).toBe(93)
    expect(s.projectiles).toHaveLength(0)
  })

  it('enemy fire that misses keeps flying', () => {
    const s = fresh()
    s.projectiles.push({
      id: 501, from: 'enemy', pos: { x: 30, y: 30 },
      vel: { x: 0, y: 0 }, radius: 5, damage: 7, ttl: 1,
    })
    step(s, [], 0.001)
    expect(s.survivor.hp).toBe(100)
    expect(s.projectiles).toHaveLength(1)
  })
})

describe('game end', () => {
  it('director wins when the survivor drops to zero', () => {
    const s = fresh()
    s.survivor.hp = 5
    makeEnemy(s, 'rusher', { x: CENTER.x, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.status).toBe('directorWon')
    expect(s.outcomeTime).toBeCloseTo(0.01)
  })

  it('survivor wins when the clock runs out', () => {
    const s = fresh(1, 0.05)
    step(s, [], 0.1)
    expect(s.status).toBe('survivorWon')
  })

  it('a kill on the final tick still counts as a director win', () => {
    const s = fresh(1, 0.05)
    s.survivor.hp = 5
    makeEnemy(s, 'rusher', { x: CENTER.x, y: CENTER.y })
    step(s, [], 0.1)
    expect(s.status).toBe('directorWon')
  })

  it('a finished game is inert', () => {
    const s = fresh(1, 0.05)
    step(s, [], 0.1)
    const t = s.t
    step(s, [], 0.1)
    expect(s.t).toBe(t)
  })

  it('director actions flow through step', () => {
    const s = fresh()
    step(s, [{ type: 'spawn', kind: 'rusher' }], 0.001)
    expect(s.enemies).toHaveLength(1)
    expect(s.director.energy).toBeLessThan(30)
  })
})
