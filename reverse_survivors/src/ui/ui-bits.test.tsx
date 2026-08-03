import { render, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Ctx2D } from '../render/draw'
import { installRaf, makeCtxStub } from '../test/harness'
import { CanvasStage } from './CanvasStage'
import { fmtTime } from './format'
import { useGameLoop } from './useGameLoop'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('fmtTime', () => {
  it('formats minutes and zero-padded seconds', () => {
    expect(fmtTime(0)).toBe('0:00')
    expect(fmtTime(65)).toBe('1:05')
    expect(fmtTime(300.9)).toBe('5:00')
  })
})

describe('useGameLoop', () => {
  it('feeds clamped dt values and swaps callbacks without restarting', () => {
    const raf = installRaf()
    const dts: number[] = []
    const cb1 = (dt: number): void => { dts.push(dt) }
    const { rerender } = renderHook(({ cb }: { cb: (dt: number) => void }) => { useGameLoop(cb) }, {
      initialProps: { cb: cb1 },
    })
    expect(raf.pending()).toBe(1)
    raf.pump(0)
    raf.pump(16)
    raf.pump(1016)
    expect(dts[0]).toBe(0)
    expect(dts[1]).toBeCloseTo(0.016)
    expect(dts[2]).toBe(0.1)

    const dts2: number[] = []
    rerender({ cb: (dt: number): void => { dts2.push(dt) } })
    raf.pump(1032)
    expect(dts2).toHaveLength(1)
    expect(dts).toHaveLength(3)
  })

  it('cancels its frame on unmount', () => {
    const raf = installRaf()
    const { unmount } = renderHook(() => { useGameLoop(() => undefined) })
    expect(raf.pending()).toBe(1)
    unmount()
    expect(raf.pending()).toBe(0)
  })
})

describe('CanvasStage', () => {
  it('hands over the 2d context when available, and null on unmount', () => {
    const stub = makeCtxStub()
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext')
      .mockImplementation(() => stub as unknown as CanvasRenderingContext2D)
    const seen: (Ctx2D | null)[] = []
    const { unmount } = render(<CanvasStage onCtx={(c) => { seen.push(c) }} />)
    expect(seen).toEqual([stub])
    unmount()
    expect(seen).toEqual([stub, null])
  })

  it('hands over null when the environment has no 2d context', () => {
    const seen: (Ctx2D | null)[] = []
    render(<CanvasStage onCtx={(c) => { seen.push(c) }} />)
    expect(seen).toEqual([null])
  })
})
