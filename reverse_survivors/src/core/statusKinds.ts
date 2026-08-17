/**
 * The status effects the survivor can be under.
 *
 * Its own module because both `types.ts` and `enemies.ts` need it: enemy specs
 * name the status they inflict, and the survivor's state carries the seconds
 * remaining per status. Keeping it here lets both import it without either
 * importing the other.
 */

export type StatusKind = 'slow' | 'suppress' | 'bleed'

export const STATUS_ORDER: readonly [StatusKind, ...StatusKind[]] = ['slow', 'suppress', 'bleed']

/** Multiplier applied to the survivor while the matching status is live. */
export const STATUS_POWER: Record<StatusKind, number> = {
  slow: 0.55, // move speed
  suppress: 1.75, // fire cooldown — higher is slower
  bleed: 0, // regen
}

export const STATUS_LABELS: Record<StatusKind, string> = {
  slow: 'mired',
  suppress: 'stifled',
  bleed: 'unknitting',
}
