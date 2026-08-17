/** Enemy behaviour, bombers and projectiles. */

import { describe, expect, it } from 'vitest'
import { createInitialState, step } from './sim'
import { makeEnemy } from './simUnit'
import type { GameState, Projectile } from './types'
import { ARENA } from './types'

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
    debuff: 'slow',
    debuffDuration: 0,
  }
  state.nextId += 1
  state.projectiles.push(p)
  return p
}

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
      debuff: 'slow', debuffDuration: 0,
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
      debuff: 'slow', debuffDuration: 0,
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
