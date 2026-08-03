export interface Vec {
  x: number
  y: number
}

export const dist = (a: Vec, b: Vec): number => Math.hypot(a.x - b.x, a.y - b.y)

/** Velocity vector of magnitude `speed` pointing from `from` to `to`. Zero when coincident. */
export const toward = (from: Vec, to: Vec, speed: number): Vec => {
  const d = dist(from, to)
  if (d === 0) {
    return { x: 0, y: 0 }
  }
  return { x: ((to.x - from.x) / d) * speed, y: ((to.y - from.y) / d) * speed }
}

export const clamp = (v: number, min: number, max: number): number =>
  Math.min(Math.max(v, min), max)
