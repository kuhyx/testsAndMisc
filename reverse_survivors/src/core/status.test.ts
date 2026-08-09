import { describe, expect, it } from 'vitest'
import { applyStatus, factor, isOn, tickStatuses } from './status'
import type { Survivor } from './types'
import { STATUS_POWER } from './types'

const sv = (): Survivor => ({
  pos: { x: 0, y: 0 },
  hp: 100,
  maxHp: 100,
  speed: 150,
  regen: 0,
  damage: 8,
  multishot: 1,
  fireCooldown: 0.55,
  fireTimer: 0,
  level: 1,
  xp: 0,
  xpNext: 20,
  kills: 0,
  statuses: { slow: 0, suppress: 0, bleed: 0 },
})

describe('isOn', () => {
  it('is 0 only at exactly zero', () => {
    expect(isOn(0)).toBe(0)
  })

  it('is 1 for any live remainder, however small', () => {
    expect(isOn(0.001)).toBe(1)
    expect(isOn(5)).toBe(1)
  })
})

describe('factor', () => {
  it('is 1 when the timer is idle', () => {
    expect(factor(0, STATUS_POWER.slow)).toBe(1)
  })

  it('is the active multiplier while the timer runs', () => {
    expect(factor(2, STATUS_POWER.slow)).toBeCloseTo(0.55)
  })

  it('supports a total shutdown multiplier', () => {
    expect(factor(1, STATUS_POWER.bleed)).toBe(0)
  })
})

describe('tickStatuses', () => {
  it('drains every timer and floors at zero', () => {
    const s = sv()
    s.statuses.slow = 1
    s.statuses.suppress = 0.4
    tickStatuses(s, 0.5)
    expect(s.statuses.slow).toBeCloseTo(0.5)
    expect(s.statuses.suppress).toBe(0)
    expect(s.statuses.bleed).toBe(0)
  })

  it('never goes negative on a large dt', () => {
    const s = sv()
    s.statuses.bleed = 1
    tickStatuses(s, 99)
    expect(s.statuses.bleed).toBe(0)
  })
})

describe('applyStatus', () => {
  it('refreshes to the longer remainder and never stacks', () => {
    const s = sv()
    applyStatus(s, 'slow', 2)
    applyStatus(s, 'slow', 1)
    expect(s.statuses.slow).toBe(2)
    applyStatus(s, 'slow', 3)
    expect(s.statuses.slow).toBe(3)
  })

  it('a zero duration is a no-op, which is how inert specs call it', () => {
    const s = sv()
    applyStatus(s, 'bleed', 0)
    expect(s.statuses.bleed).toBe(0)
  })
})
