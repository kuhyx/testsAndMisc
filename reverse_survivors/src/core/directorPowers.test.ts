/** Director powers and difficulty economy. */

import { describe, expect, it } from 'vitest'
import { applyAction, edgeSpawnPos, regenRate, tickDirector, } from './director'
import { createInitialState } from './sim'
import type { GameState } from './types'
import {
  AMBUSH_RADIUS, ARENA, ENEMY_SPECS, FRENZY_DURATION,
  POWER_COOLDOWN, POWER_COST, RIFT_DURATION,
} from './types'

const fresh = (seed = 1): GameState => createInitialState(seed)

describe('director powers', () => {
  it('power cooldowns drain and floor at zero', () => {
    const s = fresh()
    s.director.powerCooldowns.ambush = 0.3
    s.director.powerCooldowns.frenzy = 2
    tickDirector(s, 0.5)
    expect(s.director.powerCooldowns.ambush).toBe(0)
    expect(s.director.powerCooldowns.frenzy).toBeCloseTo(1.5)
  })

  it('frenzy and rift timers drain and floor at zero', () => {
    const s = fresh()
    s.director.frenzyTimer = 0.2
    s.director.riftTimer = 5
    tickDirector(s, 0.5)
    expect(s.director.frenzyTimer).toBe(0)
    expect(s.director.riftTimer).toBeCloseTo(4.5)
  })

  it('ambush lands a unit near the survivor and debits both costs', () => {
    const s = fresh()
    s.director.energy = 400
    expect(applyAction(s, { type: 'ambush', kind: 'rusher' })).toBe(true)
    expect(s.enemies).toHaveLength(1)
    const e = s.enemies[0]
    const d = Math.hypot(
      (e?.pos.x ?? 0) - s.survivor.pos.x,
      (e?.pos.y ?? 0) - s.survivor.pos.y,
    )
    expect(d).toBeCloseTo(AMBUSH_RADIUS, 5)
    expect(s.director.energy).toBe(400 - POWER_COST.ambush - ENEMY_SPECS.rusher.cost)
    expect(s.director.powerCooldowns.ambush).toBe(POWER_COOLDOWN.ambush)
  })

  it('ambush is rejected when it cannot be afforded', () => {
    const s = fresh()
    s.director.energy = 5
    expect(applyAction(s, { type: 'ambush', kind: 'rusher' })).toBe(false)
    expect(s.enemies).toHaveLength(0)
    expect(s.director.energy).toBe(5)
  })

  it('ambush is rejected while cooling', () => {
    const s = fresh()
    s.director.energy = 400
    expect(applyAction(s, { type: 'ambush', kind: 'rusher' })).toBe(true)
    expect(applyAction(s, { type: 'ambush', kind: 'rusher' })).toBe(false)
    expect(s.enemies).toHaveLength(1)
  })

  it('ambush lanes never repeat, even past a full turn', () => {
    // Regression: a 2*PI/7 step cycled silently, so index 7 reused index 0.
    const s = fresh()
    const seen: string[] = []
    for (let i = 0; i < 24; i += 1) {
      s.director.powerCooldowns.ambush = 0
      s.director.energy = 400
      s.enemies = []
      applyAction(s, { type: 'ambush', kind: 'rusher' })
      const e = s.enemies[0]
      seen.push(`${(e?.pos.x ?? 0).toFixed(6)},${(e?.pos.y ?? 0).toFixed(6)}`)
    }
    expect(new Set(seen).size).toBe(24)
  })

  it('successive ambushes rotate to a different lane, deterministically', () => {
    const angles = (): number[] => {
      const s = fresh()
      s.director.energy = 400
      const out: number[] = []
      for (let i = 0; i < 3; i += 1) {
        s.director.powerCooldowns.ambush = 0
        s.director.energy = 400
        applyAction(s, { type: 'ambush', kind: 'rusher' })
      }
      for (const e of s.enemies) {
        out.push(Math.atan2(e.pos.y - s.survivor.pos.y, e.pos.x - s.survivor.pos.x))
      }
      return out
    }
    const first = angles()
    expect(new Set(first).size).toBe(3)
    expect(angles()).toEqual(first)
  })

  it('frenzy sets its timer and debits the cost', () => {
    const s = fresh()
    s.director.energy = 400
    expect(applyAction(s, { type: 'frenzy' })).toBe(true)
    expect(s.director.frenzyTimer).toBe(FRENZY_DURATION)
    expect(s.director.energy).toBe(400 - POWER_COST.frenzy)
  })

  it('frenzy is rejected when unaffordable', () => {
    const s = fresh()
    s.director.energy = 10
    expect(applyAction(s, { type: 'frenzy' })).toBe(false)
    expect(s.director.frenzyTimer).toBe(0)
  })

  it('a rift pins every spawn to the chosen edge', () => {
    const s = fresh()
    s.director.energy = 400
    expect(applyAction(s, { type: 'rift', edge: 2 })).toBe(true)
    expect(s.director.riftTimer).toBe(RIFT_DURATION)
    for (let i = 0; i < 20; i += 1) {
      expect(edgeSpawnPos(s).x).toBe(0)
    }
  })

  it('once the rift closes, all four edges return', () => {
    const s = fresh(7)
    s.director.riftTimer = 0
    const seen = new Set<string>()
    for (let i = 0; i < 40; i += 1) {
      const p = edgeSpawnPos(s)
      seen.add(`${String(p.x === 0 || p.x === ARENA.w)}-${String(p.y === 0 || p.y === ARENA.h)}`)
    }
    expect(seen.size).toBeGreaterThan(1)
  })

  it('a rift is rejected when unaffordable', () => {
    const s = fresh()
    s.director.energy = 1
    expect(applyAction(s, { type: 'rift', edge: 1 })).toBe(false)
    expect(s.director.riftTimer).toBe(0)
  })
})

describe('difficulty economy', () => {
  it('regen defaults to a rate of 1', () => {
    expect(regenRate(0)).toBe(6)
    expect(regenRate(30)).toBe(8)
  })

  it('regen scales with the tier rate', () => {
    expect(regenRate(0, 1.25)).toBeCloseTo(7.5)
    expect(regenRate(0, 0.85)).toBeCloseTo(5.1)
  })
})
