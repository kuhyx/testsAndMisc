import type { Mock } from 'vitest'
import { vi } from 'vitest'
import type { Ctx2D } from '../render/draw'

export interface RafHarness {
  /** Fire all queued frame callbacks with the given timestamp (ms). */
  pump: (ts: number) => void
  pending: () => number
  restore: () => void
}

export const installRaf = (): RafHarness => {
  let queue: FrameRequestCallback[] = []
  let nextHandle = 0
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback): number => {
    queue.push(cb)
    nextHandle += 1
    return nextHandle
  })
  vi.stubGlobal('cancelAnimationFrame', (): void => {
    queue = []
  })
  return {
    pump: (ts: number): void => {
      const batch = queue
      queue = []
      for (const cb of batch) {
        cb(ts)
      }
    },
    pending: (): number => queue.length,
    restore: (): void => {
      vi.unstubAllGlobals()
    },
  }
}

export interface CtxStub extends Ctx2D {
  fillRect: Mock<(x: number, y: number, w: number, h: number) => void>
  beginPath: Mock<() => void>
  arc: Mock<(x: number, y: number, r: number, a0: number, a1: number) => void>
  fill: Mock<() => void>
  stroke: Mock<() => void>
}

export const makeCtxStub = (): CtxStub => ({
  fillStyle: '',
  strokeStyle: '',
  lineWidth: 0,
  globalAlpha: 1,
  fillRect: vi.fn<(x: number, y: number, w: number, h: number) => void>(),
  beginPath: vi.fn<() => void>(),
  arc: vi.fn<(x: number, y: number, r: number, a0: number, a1: number) => void>(),
  fill: vi.fn<() => void>(),
  stroke: vi.fn<() => void>(),
})
