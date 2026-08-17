/** Frenzy, difficulty tiers and damage channels. */

/** Splitters, new units and status effects. */

/** Enemy behaviour, bombers and projectiles. */

import { describe, expect, it } from 'vitest'
import { createInitialState, step } from './sim'
import { makeEnemy } from './simUnit'
import type { GameState } from './types'
import { ARENA, DIFFICULTIES, FRENZY_DAMAGE, FRENZY_SPEED } from './types'

const CENTER = { x: ARENA.w / 2, y: ARENA.h / 2 }

const fresh = (seed = 1, duration?: number): GameState =>
  duration === undefined ? createInitialState(seed) : createInitialState(seed, duration)


describe('frenzy', () => {
  it('speeds the horde while it lasts', () => {
    const base = fresh()
    const b = makeEnemy(base, 'rusher', { x: CENTER.x + 300, y: CENTER.y })
    step(base, [], 0.05)
    const normal = CENTER.x + 300 - b.pos.x

    const hyped = fresh()
    hyped.director.frenzyTimer = 5
    const h = makeEnemy(hyped, 'rusher', { x: CENTER.x + 300, y: CENTER.y })
    step(hyped, [], 0.05)
    const rushed = CENTER.x + 300 - h.pos.x

    expect(rushed).toBeCloseTo(normal * FRENZY_SPEED, 5)
  })

  it('raises contact damage while it lasts', () => {
    const s = fresh()
    s.director.frenzyTimer = 5
    makeEnemy(s, 'rusher', { x: CENTER.x, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.survivor.hp).toBeCloseTo(100 - 6 * FRENZY_DAMAGE, 5)
  })

  it('expires back to baseline speed', () => {
    const s = fresh()
    s.director.frenzyTimer = 0.01
    const e = makeEnemy(s, 'rusher', { x: CENTER.x + 300, y: CENTER.y })
    step(s, [], 0.5)
    expect(s.director.frenzyTimer).toBe(0)
    const after = e.pos.x
    step(s, [], 0.05)
    const moved = after - e.pos.x
    expect(moved).toBeCloseTo(170 * 0.05, 5)
  })
})

describe('difficulty tiers', () => {
  it('defaults to normal, the identity tier', () => {
    const s = fresh()
    expect(s.difficulty).toBe(DIFFICULTIES.normal)
    expect(s.survivor.maxHp).toBe(100)
  })

  it('accepts an explicit tier', () => {
    const s = createInitialState(1, undefined, 'crusade')
    expect(s.difficulty).toBe(DIFFICULTIES.crusade)
  })

  it('takes its duration from the tier when none is given', () => {
    expect(createInitialState(1, undefined, 'haunting').duration)
      .toBe(DIFFICULTIES.haunting.duration)
  })

  it('an explicit duration still wins over the tier', () => {
    expect(createInitialState(1, 42, 'haunting').duration).toBe(42)
  })

  it('scales enemy hp', () => {
    const s = createInitialState(1, undefined, 'crusade')
    const e = makeEnemy(s, 'rusher', { x: 0, y: 0 })
    expect(e.hp).toBeCloseTo(14 * DIFFICULTIES.crusade.enemyHp, 5)
  })

  it('scales survivor hp', () => {
    const s = createInitialState(1, undefined, 'haunting')
    expect(s.survivor.maxHp).toBe(125)
  })

  it('scales enemy speed', () => {
    const s = createInitialState(1, undefined, 'crusade')
    const e = makeEnemy(s, 'rusher', { x: CENTER.x + 300, y: CENTER.y })
    step(s, [], 0.05)
    const moved = CENTER.x + 300 - e.pos.x
    expect(moved).toBeCloseTo(170 * DIFFICULTIES.crusade.enemySpeed * 0.05, 5)
  })
})

describe('frenzy damage reaches every channel', () => {
  // Regression: frenzy multiplied contact damage only, so ranged and blast
  // units — including the bomber, whose whole purpose is damage — ignored it.
  const dealt = (frenzied: boolean, kind: 'warden' | 'artillery' | 'bomber', at: number): number => {
    const s = fresh(3)
    s.survivor.hp = 1e6
    s.survivor.maxHp = 1e6
    s.survivor.speed = 0
    s.duration = 1e6
    if (frenzied) {
      s.director.frenzyTimer = 1e6
    }
    makeEnemy(s, kind, { x: CENTER.x + at, y: CENTER.y })
    const before = s.survivor.hp
    for (let i = 0; i < 360; i += 1) {
      step(s, [], 1 / 60)
    }
    return before - s.survivor.hp
  }

  it('scales contact damage', () => {
    expect(dealt(true, 'warden', 0)).toBeCloseTo(dealt(false, 'warden', 0) * FRENZY_DAMAGE, 5)
  })

  it('scales ranged damage', () => {
    expect(dealt(true, 'artillery', 300))
      .toBeCloseTo(dealt(false, 'artillery', 300) * FRENZY_DAMAGE, 5)
  })

  it('scales blast damage', () => {
    expect(dealt(true, 'bomber', 0)).toBeCloseTo(dealt(false, 'bomber', 0) * FRENZY_DAMAGE, 5)
  })
})
