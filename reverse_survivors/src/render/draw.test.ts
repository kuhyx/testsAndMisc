import { describe, expect, it } from 'vitest'
import { createInitialState, makeEnemy } from '../core/sim'
import type { GameState } from '../core/types'
import { makeCtxStub } from '../test/harness'
import { draw } from './draw'

const fresh = (): GameState => createInitialState(1)

// Empty state baseline: ritual circle + survivor halo + body + hp ring.
const BASE = { beginPath: 4, arc: 4, fill: 2, stroke: 2, fillRect: 1 }

describe('draw', () => {
  it('paints the empty arena baseline', () => {
    const ctx = makeCtxStub()
    draw(ctx, fresh())
    expect(ctx.fillRect).toHaveBeenCalledTimes(BASE.fillRect)
    expect(ctx.beginPath).toHaveBeenCalledTimes(BASE.beginPath)
    expect(ctx.arc).toHaveBeenCalledTimes(BASE.arc)
    expect(ctx.fill).toHaveBeenCalledTimes(BASE.fill)
    expect(ctx.stroke).toHaveBeenCalledTimes(BASE.stroke)
  })

  it('paints projectiles from both sides', () => {
    const ctx = makeCtxStub()
    const s = fresh()
    s.projectiles.push(
      { id: 1, from: 'survivor', pos: { x: 10, y: 10 }, vel: { x: 0, y: 0 }, radius: 4, damage: 1, ttl: 1 },
      { id: 2, from: 'enemy', pos: { x: 20, y: 20 }, vel: { x: 0, y: 0 }, radius: 5, damage: 1, ttl: 1 },
    )
    draw(ctx, s)
    expect(ctx.fill).toHaveBeenCalledTimes(BASE.fill + 2)
    expect(ctx.arc).toHaveBeenCalledTimes(BASE.arc + 2)
  })

  it('a fresh grunt gets a body but no ring and no hp arc', () => {
    const ctx = makeCtxStub()
    const s = fresh()
    makeEnemy(s, 'rusher', { x: 100, y: 100 })
    draw(ctx, s)
    expect(ctx.fill).toHaveBeenCalledTimes(BASE.fill + 1)
    expect(ctx.stroke).toHaveBeenCalledTimes(BASE.stroke)
  })

  it('a damaged enemy shows an hp arc', () => {
    const ctx = makeCtxStub()
    const s = fresh()
    const tank = makeEnemy(s, 'tank', { x: 100, y: 100 })
    tank.hp = 60
    draw(ctx, s)
    expect(ctx.fill).toHaveBeenCalledTimes(BASE.fill + 1)
    expect(ctx.stroke).toHaveBeenCalledTimes(BASE.stroke + 1)
  })

  it('bosses wear a blood ring', () => {
    const ctx = makeCtxStub()
    const s = fresh()
    makeEnemy(s, 'colossus', { x: 100, y: 100 })
    draw(ctx, s)
    expect(ctx.fill).toHaveBeenCalledTimes(BASE.fill + 1)
    expect(ctx.stroke).toHaveBeenCalledTimes(BASE.stroke + 1)
    expect(ctx.arc).toHaveBeenCalledTimes(BASE.arc + 2)
  })
})
