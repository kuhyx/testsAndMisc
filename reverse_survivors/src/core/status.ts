import type { StatusKind, Survivor } from './types'
import { STATUS_ORDER } from './types'

/**
 * 1 while the timer is live, 0 once it has expired.
 *
 * Deliberately arithmetic rather than `timer > 0`: every consumer of this value
 * multiplies by it, so an `if` here would add a branch pair per status per
 * consumer — the coverage gate is 100 % and those branches buy nothing.
 * Timers only reach 0 via `Math.max(0, t - dt)`, so the domain is [0, inf).
 */
export const isOn = (timer: number): number => Math.min(1, Math.ceil(timer))

/** `active` while the timer runs, 1 when idle. Branch-free blend. */
export const factor = (timer: number, active: number): number =>
  1 - isOn(timer) * (1 - active)

export const tickStatuses = (sv: Survivor, dt: number): void => {
  for (const kind of STATUS_ORDER) {
    sv.statuses[kind] = Math.max(0, sv.statuses[kind] - dt)
  }
}

/**
 * Refresh-not-stack: re-applying extends the timer, never compounds it.
 * This is what caps a horde's total lockdown at one status duration — the
 * guarantee is structural, not a tuned number.
 *
 * A 0-second duration is a no-op, which is how non-debuffing enemies call this
 * unconditionally without needing a guard branch.
 */
export const applyStatus = (sv: Survivor, kind: StatusKind, seconds: number): void => {
  sv.statuses[kind] = Math.max(sv.statuses[kind], seconds)
}
