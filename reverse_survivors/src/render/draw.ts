import { FIRE_RANGE, SURVIVOR_RADIUS } from '../core/sim'
import type { EnemyKind, GameState } from '../core/types'
import { ARENA, ENEMY_SPECS, STATUS_ORDER } from '../core/types'

/** Structural subset of CanvasRenderingContext2D — stubbable in tests. */
export interface Ctx2D {
  fillStyle: string | CanvasGradient | CanvasPattern
  strokeStyle: string | CanvasGradient | CanvasPattern
  lineWidth: number
  globalAlpha: number
  fillRect: (x: number, y: number, w: number, h: number) => void
  beginPath: () => void
  arc: (x: number, y: number, r: number, a0: number, a1: number) => void
  fill: () => void
  stroke: () => void
}

const COLORS = {
  void: '#140b1c',
  ring: '#2b1a3a',
  bone: '#e8dcc8',
  holy: '#7ce0c3',
  holyDim: '#2e5c50',
  blood: '#c94f7c',
  arcane: '#b06ce8',
} as const

const ENEMY_COLORS: Record<EnemyKind, string> = {
  rusher: '#c94f7c',
  stalker: '#b06ce8',
  tank: '#8a4b3c',
  bomber: '#e0a13d',
  splitter: '#5fae6b',
  artillery: '#d4693a',
  warden: '#e6d15c',
  colossus: '#7d2c50',
  hivemind: '#5a3d8a',
  leech: '#3f7d6e',
}

const IS_BOSS: Record<EnemyKind, boolean> = {
  rusher: false,
  stalker: false,
  tank: false,
  bomber: false,
  splitter: false,
  artillery: false,
  warden: false,
  colossus: true,
  hivemind: true,
  leech: true,
}

const circle = (ctx: Ctx2D, x: number, y: number, r: number): void => {
  ctx.beginPath()
  ctx.arc(x, y, r, 0, Math.PI * 2)
}

export const draw = (ctx: Ctx2D, state: GameState): void => {
  ctx.globalAlpha = 1
  ctx.fillStyle = COLORS.void
  ctx.fillRect(0, 0, ARENA.w, ARENA.h)

  // Ritual circle: the survivor's consecrated ground.
  ctx.globalAlpha = 0.5
  ctx.strokeStyle = COLORS.ring
  ctx.lineWidth = 2
  circle(ctx, ARENA.w / 2, ARENA.h / 2, 150)
  ctx.stroke()
  ctx.globalAlpha = 1

  for (const p of state.projectiles) {
    ctx.fillStyle = p.from === 'survivor' ? COLORS.holy : COLORS.blood
    circle(ctx, p.pos.x, p.pos.y, p.radius)
    ctx.fill()
  }

  for (const e of state.enemies) {
    const spec = ENEMY_SPECS[e.kind]
    ctx.fillStyle = ENEMY_COLORS[e.kind]
    circle(ctx, e.pos.x, e.pos.y, spec.radius)
    ctx.fill()
    if (IS_BOSS[e.kind]) {
      ctx.strokeStyle = COLORS.blood
      ctx.lineWidth = 3
      circle(ctx, e.pos.x, e.pos.y, spec.radius + 6)
      ctx.stroke()
    }
    if (e.hp < spec.hp) {
      ctx.strokeStyle = COLORS.bone
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(e.pos.x, e.pos.y, spec.radius + 3, -Math.PI / 2, -Math.PI / 2 + (e.hp / spec.hp) * Math.PI * 2)
      ctx.stroke()
    }
  }

  const sv = state.survivor
  ctx.globalAlpha = 0.12
  ctx.fillStyle = COLORS.holy
  circle(ctx, sv.pos.x, sv.pos.y, FIRE_RANGE)
  ctx.fill()
  ctx.globalAlpha = 1
  ctx.fillStyle = COLORS.holy
  circle(ctx, sv.pos.x, sv.pos.y, SURVIVOR_RADIUS)
  ctx.fill()
  ctx.strokeStyle = COLORS.holyDim
  ctx.lineWidth = 3
  ctx.beginPath()
  ctx.arc(
    sv.pos.x, sv.pos.y, SURVIVOR_RADIUS + 5,
    -Math.PI / 2, -Math.PI / 2 + (Math.max(0, sv.hp) / sv.maxHp) * Math.PI * 2,
  )
  ctx.stroke()

  // Afflicted halo. Gated so an unafflicted survivor draws exactly as before.
  const afflicted = STATUS_ORDER.some((kind) => sv.statuses[kind] > 0)
  if (afflicted) {
    ctx.strokeStyle = COLORS.arcane
    ctx.lineWidth = 2
    circle(ctx, sv.pos.x, sv.pos.y, SURVIVOR_RADIUS + 10)
    ctx.stroke()
  }
}
