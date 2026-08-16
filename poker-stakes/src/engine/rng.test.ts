import { describe, expect, it } from 'vitest'
import { createRng, nextFloat, nextInt, pick } from './rng'

describe('rng', () => {
  it('is deterministic for a given seed', () => {
    const a = createRng(123)
    const b = createRng(123)
    expect([nextFloat(a), nextFloat(a), nextFloat(a)]).toEqual([
      nextFloat(b),
      nextFloat(b),
      nextFloat(b),
    ])
  })

  it('produces different sequences for different seeds', () => {
    expect(nextFloat(createRng(1))).not.toBe(nextFloat(createRng(2)))
  })

  it('stays within [0, 1)', () => {
    const rng = createRng(77)
    for (let i = 0; i < 200; i += 1) {
      const v = nextFloat(rng)
      expect(v).toBeGreaterThanOrEqual(0)
      expect(v).toBeLessThan(1)
    }
  })

  it('wraps negative seeds into unsigned space', () => {
    expect(createRng(-1).s).toBe(0xffffffff)
  })

  it('nextInt stays within [0, max)', () => {
    const rng = createRng(9)
    for (let i = 0; i < 100; i += 1) {
      const v = nextInt(rng, 4)
      expect(v).toBeGreaterThanOrEqual(0)
      expect(v).toBeLessThan(4)
    }
  })

  it('pick eventually returns every element of a tuple', () => {
    const rng = createRng(5)
    const seen = new Set<string>()
    for (let i = 0; i < 64; i += 1) {
      seen.add(pick(rng, ['a', 'b', 'c'] as const))
    }
    expect(seen).toEqual(new Set(['a', 'b', 'c']))
  })

  it('pick is deterministic', () => {
    expect(pick(createRng(42), [10, 20, 30] as const)).toBe(
      pick(createRng(42), [10, 20, 30] as const),
    )
  })
})
