import { describe, expect, it } from 'vitest'
import {
  applyUpgrade, createInitialState, DANGER_RADIUS, grantXp, makeEnemy, SPLIT_RADIUS, step,
  xpForLevel,
} from './sim'
import type { GameState, Projectile } from './types'
import {
  ARENA, FRENZY_DAMAGE, FRENZY_SPEED, GAME_DURATION, STATUS_POWER,
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
