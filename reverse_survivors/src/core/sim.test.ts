import { describe, expect, it } from 'vitest'
import {
  applyUpgrade, createInitialState, DANGER_RADIUS, grantXp, makeEnemy, step,
  xpForLevel,
} from './sim'
import type { GameState, } from './types'
import {
  ARENA, GAME_DURATION, } from './types'

const CENTER = { x: ARENA.w / 2, y: ARENA.h / 2 }

const fresh = (seed = 1, duration?: number): GameState =>
  duration === undefined ? createInitialState(seed) : createInitialState(seed, duration)


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
