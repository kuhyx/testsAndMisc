import { useEffect, useRef } from 'react'

/** Runs `onFrame(dtSeconds)` on every animation frame. dt is clamped to 100 ms. */
export const useGameLoop = (onFrame: (dt: number) => void): void => {
  const cbRef = useRef(onFrame)
  useEffect(() => {
    cbRef.current = onFrame
  })
  useEffect(() => {
    let handle = 0
    let last = -1
    const tick = (ts: number): void => {
      if (last < 0) {
        last = ts
      }
      const dt = Math.min((ts - last) / 1000, 0.1)
      last = ts
      cbRef.current(dt)
      handle = requestAnimationFrame(tick)
    }
    handle = requestAnimationFrame(tick)
    return (): void => {
      cancelAnimationFrame(handle)
    }
  }, [])
}
