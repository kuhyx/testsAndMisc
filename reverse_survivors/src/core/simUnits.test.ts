/** Splitters, new units and status effects. */

/** Enemy behaviour, bombers and projectiles. */

import { describe, expect, it } from 'vitest'
import {
  createInitialState, makeEnemy, SPLIT_RADIUS, step,
  } from './sim'
import type { GameState, Projectile } from './types'
import {
  ARENA, STATUS_POWER,
} from './types'

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

describe('splitter', () => {
  it('dies into three rushers at fixed offsets', () => {
    const s = fresh()
    const sp = makeEnemy(s, 'splitter', { x: 300, y: 300 })
    shot(s, 300, 300, 999)
    step(s, [], 0.001)
    const children = s.enemies.filter((e) => e.id !== sp.id)
    expect(children).toHaveLength(3)
    expect(children.every((c) => c.kind === 'rusher')).toBe(true)
    // Children drift toward the survivor within the same tick, so assert the
    // spawn ring loosely — the exact geometry is pinned by the test below.
    for (const c of children) {
      expect(Math.hypot(c.pos.x - 300, c.pos.y - 300)).toBeLessThan(SPLIT_RADIUS + 5)
    }
  })

  it('spawns children on a ring at 120-degree offsets', () => {
    const s = fresh()
    makeEnemy(s, 'splitter', { x: 300, y: 300 })
    shot(s, 300, 300, 999)
    // dt of 0 isolates the spawn geometry from the movement that follows it.
    step(s, [], 0)
    const angles = s.enemies
      .map((e) => Math.atan2(e.pos.y - 300, e.pos.x - 300))
      .sort((a, b) => a - b)
    expect(angles).toHaveLength(3)
    // Pairwise gaps without indexing (noUncheckedIndexedAccess would widen those).
    const gaps: number[] = []
    let prev: number | null = null
    for (const a of angles) {
      if (prev !== null) {
        gaps.push(a - prev)
      }
      prev = a
    }
    expect(gaps).toHaveLength(2)
    for (const g of gaps) {
      expect(g).toBeCloseTo((Math.PI * 2) / 3, 5)
    }
  })

  it('children are deterministic and draw no RNG', () => {
    const run = (): { x: number; y: number }[] => {
      const s = fresh(42)
      makeEnemy(s, 'splitter', { x: 300, y: 300 })
      shot(s, 300, 300, 999)
      step(s, [], 0.001)
      return s.enemies.map((e) => ({ x: e.pos.x, y: e.pos.y }))
    }
    expect(run()).toEqual(run())
  })

  it('clamps children into the arena when it dies in a corner', () => {
    const s = fresh()
    makeEnemy(s, 'splitter', { x: 2, y: 2 })
    shot(s, 2, 2, 999)
    step(s, [], 0.001)
    for (const e of s.enemies) {
      expect(e.pos.x).toBeGreaterThanOrEqual(10)
      expect(e.pos.y).toBeGreaterThanOrEqual(10)
    }
  })

  it('a later projectile in the same tick can hit a fresh child', () => {
    const s = fresh()
    makeEnemy(s, 'splitter', { x: 300, y: 300 })
    shot(s, 300, 300, 999)
    shot(s, 300 + SPLIT_RADIUS, 300, 999)
    step(s, [], 0.001)
    expect(s.survivor.kills).toBe(2)
  })

  it('non-splitting kinds spawn no children', () => {
    const s = fresh()
    makeEnemy(s, 'rusher', { x: 300, y: 300 })
    shot(s, 300, 300, 999)
    step(s, [], 0.001)
    expect(s.enemies).toHaveLength(0)
  })
})

describe('new units', () => {
  it('artillery outranges the survivor and fires while it cannot', () => {
    const s = fresh()
    const a = makeEnemy(s, 'artillery', { x: CENTER.x + 400, y: CENTER.y })
    a.fireTimer = 0
    step(s, [], 0.001)
    expect(s.projectiles.some((p) => p.from === 'enemy')).toBe(true)
    expect(s.projectiles.some((p) => p.from === 'survivor')).toBe(false)
  })

  it('artillery holds station at its keep distance', () => {
    const s = fresh()
    const a = makeEnemy(s, 'artillery', { x: CENTER.x + 420, y: CENTER.y })
    const before = a.pos.x
    step(s, [], 0.016)
    expect(a.pos.x).toBeCloseTo(before, 5)
  })

  it('warden closes faster than a rusher', () => {
    const s = fresh()
    const w = makeEnemy(s, 'warden', { x: CENTER.x + 300, y: CENTER.y })
    const r = makeEnemy(s, 'rusher', { x: CENTER.x + 300, y: CENTER.y })
    step(s, [], 0.016)
    expect(CENTER.x + 300 - w.pos.x).toBeGreaterThan(CENTER.x + 300 - r.pos.x)
  })

  it('the hivemind still births rushers via spawnKind', () => {
    const s = fresh()
    const h = makeEnemy(s, 'hivemind', { x: 40, y: 40 })
    h.spawnTimer = 0
    step(s, [], 0.001)
    expect(s.enemies.some((e) => e.kind === 'rusher')).toBe(true)
  })
})

describe('status effects', () => {
  it('a warden contact mires the survivor and halves its movement', () => {
    const slowed = fresh()
    slowed.survivor.pos = { x: 100, y: CENTER.y }
    makeEnemy(slowed, 'warden', { x: 100, y: CENTER.y })
    step(slowed, [], 0.01)
    // Statuses tick in survivorStep, which runs before enemiesStep applies
    // contact — so a status landing this tick starts at its full duration.
    expect(slowed.survivor.statuses.slow).toBe(2.0)

    // Control: same displacement, an enemy that inflicts nothing.
    const control = fresh()
    control.survivor.pos = { x: 100, y: CENTER.y }
    makeEnemy(control, 'rusher', { x: 100, y: CENTER.y })
    step(control, [], 0.01)
    expect(control.survivor.statuses.slow).toBe(0)

    const before = { slowed: slowed.survivor.pos.x, control: control.survivor.pos.x }
    slowed.enemies = []
    control.enemies = []
    step(slowed, [], 0.05)
    step(control, [], 0.05)
    const movedSlowed = slowed.survivor.pos.x - before.slowed
    const movedControl = control.survivor.pos.x - before.control
    expect(movedSlowed).toBeCloseTo(movedControl * STATUS_POWER.slow, 5)
  })

  it('slow expires and full speed returns', () => {
    const s = fresh()
    s.survivor.pos = { x: 100, y: CENTER.y }
    s.survivor.statuses.slow = 0.02
    step(s, [], 0.05)
    expect(s.survivor.statuses.slow).toBe(0)
  })

  it('an artillery shell stifles the survivor and lengthens its reload', () => {
    const s = fresh()
    s.projectiles.push({
      id: 900, from: 'enemy', pos: { x: CENTER.x, y: CENTER.y },
      vel: { x: 0, y: 0 }, radius: 5, damage: 13, ttl: 1,
      debuff: 'suppress', debuffDuration: 2.5,
    })
    makeEnemy(s, 'tank', { x: CENTER.x + 200, y: CENTER.y })
    step(s, [], 0.001)
    expect(s.survivor.statuses.suppress).toBeGreaterThan(0)
    // The shot fired this tick reloaded before the status landed; the next one pays.
    s.survivor.fireTimer = 0
    step(s, [], 0.001)
    expect(s.survivor.fireTimer).toBeCloseTo(0.55 * STATUS_POWER.suppress, 5)
  })

  it('a leech contact blocks regeneration until it expires', () => {
    const s = fresh()
    s.survivor.regen = 5
    s.survivor.hp = 50
    makeEnemy(s, 'leech', { x: CENTER.x, y: CENTER.y })
    const hp0 = s.survivor.hp
    step(s, [], 0.1)
    // Contact damage lands and regen is suppressed, so hp cannot have risen.
    expect(s.survivor.hp).toBeLessThan(hp0)
    expect(s.survivor.statuses.bleed).toBeGreaterThan(0)

    s.enemies = []
    s.survivor.statuses.bleed = 0
    const hp1 = s.survivor.hp
    step(s, [], 0.1)
    expect(s.survivor.hp).toBeGreaterThan(hp1)
  })

  it('repeated warden contacts refresh rather than stack', () => {
    const s = fresh()
    makeEnemy(s, 'warden', { x: CENTER.x, y: CENTER.y })
    makeEnemy(s, 'warden', { x: CENTER.x, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.survivor.statuses.slow).toBeLessThanOrEqual(2.0)
  })

  it('a plain rusher inflicts no status at all', () => {
    const s = fresh()
    makeEnemy(s, 'rusher', { x: CENTER.x, y: CENTER.y })
    step(s, [], 0.01)
    expect(s.survivor.statuses).toEqual({ slow: 0, suppress: 0, bleed: 0 })
  })

  it('survivor fire never debuffs the survivor', () => {
    const s = fresh()
    makeEnemy(s, 'tank', { x: CENTER.x + 200, y: CENTER.y })
    step(s, [], 0.001)
    const own = s.projectiles.find((p) => p.from === 'survivor')
    expect(own?.debuffDuration).toBe(0)
  })
})
