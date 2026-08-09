import { describe, expect, it } from 'vitest'
import { applyAction, edgeSpawnPos, regenRate, tickDirector, waveCost } from './director'
import { createInitialState } from './sim'
import { snapshotOf } from './snapshot'
import type { GameState } from './types'
import {
  AMBUSH_RADIUS, ARENA, BOSS_COOLDOWN, ENEMY_SPECS, ENERGY_CAP, FRENZY_DURATION,
  POWER_COOLDOWN, POWER_COST, RIFT_DURATION,
} from './types'

const fresh = (seed = 1): GameState => createInitialState(seed)

describe('economy', () => {
  it('regen ramps every 30 seconds', () => {
    expect(regenRate(0)).toBe(6)
    expect(regenRate(29.9)).toBe(6)
    expect(regenRate(30)).toBe(8)
    expect(regenRate(90)).toBe(12)
  })

  it('wave cost escalates', () => {
    expect(waveCost(0)).toBe(60)
    expect(waveCost(3)).toBe(135)
  })

  it('energy accrues and caps', () => {
    const s = fresh()
    s.director.energy = ENERGY_CAP - 0.1
    tickDirector(s, 1)
    expect(s.director.energy).toBe(ENERGY_CAP)
  })

  it('boss cooldowns tick down and floor at zero', () => {
    const s = fresh()
    s.director.bossCooldowns.colossus = 0.5
    tickDirector(s, 1)
    expect(s.director.bossCooldowns.colossus).toBe(0)
  })
})

describe('edge spawns', () => {
  it('always lands on an arena edge, and all four edges occur', () => {
    const s = fresh(7)
    const edges = new Set<string>()
    for (let i = 0; i < 40; i += 1) {
      const p = edgeSpawnPos(s)
      const onEdge =
        p.y === 0 ? 'top'
        : p.y === ARENA.h ? 'bottom'
        : p.x === 0 ? 'left'
        : p.x === ARENA.w ? 'right'
        : 'off'
      edges.add(onEdge)
    }
    expect(edges.has('off')).toBe(false)
    expect(edges).toEqual(new Set(['top', 'bottom', 'left', 'right']))
  })
})

describe('spawning units', () => {
  it('deducts energy and adds the enemy', () => {
    const s = fresh()
    expect(applyAction(s, { type: 'spawn', kind: 'rusher' })).toBe(true)
    expect(s.director.energy).toBe(20)
    expect(s.enemies).toHaveLength(1)
  })

  it('rejects what the director cannot afford', () => {
    const s = fresh()
    expect(applyAction(s, { type: 'spawn', kind: 'tank' })).toBe(false)
    expect(s.enemies).toHaveLength(0)
    expect(s.director.energy).toBe(30)
  })
})

describe('waves', () => {
  it('first wave rings six rushers around the survivor', () => {
    const s = fresh()
    s.director.energy = 100
    expect(applyAction(s, { type: 'wave' })).toBe(true)
    expect(s.enemies).toHaveLength(6)
    expect(s.enemies.every((e) => e.kind === 'rusher')).toBe(true)
    expect(s.director.waveIndex).toBe(1)
  })

  it('later waves grow and mix in stalkers', () => {
    const s = fresh()
    s.director.energy = 400
    applyAction(s, { type: 'wave' })
    applyAction(s, { type: 'wave' })
    expect(s.enemies).toHaveLength(6 + 9)
    expect(s.enemies.filter((e) => e.kind === 'stalker')).toHaveLength(1)
  })

  it('rejects an unaffordable wave', () => {
    const s = fresh()
    expect(applyAction(s, { type: 'wave' })).toBe(false)
    expect(s.enemies).toHaveLength(0)
  })
})

describe('bosses', () => {
  it('locked before the unlock time', () => {
    const s = fresh()
    s.director.energy = 400
    expect(applyAction(s, { type: 'boss', kind: 'colossus' })).toBe(false)
  })

  it('rejected while cooling down', () => {
    const s = fresh()
    s.t = 60
    s.director.energy = 400
    expect(applyAction(s, { type: 'boss', kind: 'colossus' })).toBe(true)
    s.director.energy = 400
    expect(applyAction(s, { type: 'boss', kind: 'colossus' })).toBe(false)
  })

  it('rejected when unaffordable', () => {
    const s = fresh()
    s.t = 60
    s.director.energy = 10
    expect(applyAction(s, { type: 'boss', kind: 'colossus' })).toBe(false)
  })

  it('summoning pays, spawns, and starts the cooldown', () => {
    const s = fresh()
    s.t = 120
    s.director.energy = 400
    expect(applyAction(s, { type: 'boss', kind: 'hivemind' })).toBe(true)
    expect(s.director.energy).toBe(400 - 220)
    expect(s.enemies[0]?.kind).toBe('hivemind')
    expect(s.director.bossCooldowns.hivemind).toBe(BOSS_COOLDOWN.hivemind)
  })
})

describe('snapshot', () => {
  it('derives affordability both ways', () => {
    const s = fresh()
    const snap = snapshotOf(s)
    expect(snap.units.find((u) => u.kind === 'rusher')?.affordable).toBe(true)
    expect(snap.units.find((u) => u.kind === 'tank')?.affordable).toBe(false)
    expect(snap.waveAffordable).toBe(false)
    s.director.energy = 300
    expect(snapshotOf(s).waveAffordable).toBe(true)
  })

  it('reports boss phases: locked, cooling, ready', () => {
    const s = fresh()
    expect(snapshotOf(s).bosses[0]?.phase).toBe('locked')
    s.t = 61
    s.director.bossCooldowns.colossus = 5
    expect(snapshotOf(s).bosses[0]?.phase).toBe('cooling')
    s.director.bossCooldowns.colossus = 0
    expect(snapshotOf(s).bosses[0]?.phase).toBe('ready')
    expect(snapshotOf(s).bosses[0]?.unlockIn).toBe(0)
  })

  it('keeps only the last three upgrades, numbered', () => {
    const s = fresh()
    s.upgrades = ['damage', 'speed', 'regen', 'multishot']
    const snap = snapshotOf(s)
    expect(snap.upgrades).toEqual([
      { n: 2, id: 'speed' },
      { n: 3, id: 'regen' },
      { n: 4, id: 'multishot' },
    ])
  })

  it('floors the reported survivor hp at zero', () => {
    const s = fresh()
    s.survivor.hp = -12
    expect(snapshotOf(s).survivorHp).toBe(0)
  })
})

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
