import { describe, expect, it } from 'vitest'
import { applyAction, edgeSpawnPos, regenRate, tickDirector, waveCost } from './director'
import { createInitialState } from './sim'
import { snapshotOf } from './snapshot'
import type { GameState } from './types'
import {
  ARENA, BOSS_COOLDOWN, ENERGY_CAP, } from './types'

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
