/**
 * The enemy roster: what kinds exist, the shape of a unit's stat block, and the
 * table of every unit's and boss's numbers.
 *
 * Split out of `types.ts` because it is data rather than vocabulary — this is
 * the file to edit when balancing, and the one that grows when a new kind is
 * added. It imports only the status vocabulary it annotates specs with, so it
 * stays a leaf alongside `types.ts` rather than depending on it circularly.
 */

import type { StatusKind } from './statusKinds'

export type UnitKind =
  | 'rusher' | 'stalker' | 'tank' | 'bomber' | 'splitter' | 'artillery' | 'warden'
export type BossKind = 'colossus' | 'hivemind' | 'leech'
export type EnemyKind = UnitKind | BossKind
export type MoveMode = 'chase' | 'skirmish'

export interface EnemySpec {
  readonly name: string
  readonly cost: number
  readonly hp: number
  readonly speed: number
  readonly radius: number
  readonly contactDamage: number
  readonly xp: number
  readonly move: MoveMode
  /** 0 disables ranged fire. */
  readonly projDamage: number
  readonly projSpeed: number
  readonly fireRange: number
  readonly fireCooldown: number
  readonly keepDistance: number
  /** True: dies on contact and blasts. */
  readonly detonates: boolean
  readonly blastRadius: number
  readonly blastDamage: number
  /** 0 disables minion spawning. */
  readonly spawnEvery: number
  /** What `spawnEvery` and `splitCount` emit. Always a kind — the `> 0` gates guard every read. */
  readonly spawnKind: UnitKind
  /** 0 disables on-death splitting. */
  readonly splitCount: number
  /** Status inflicted on contact (or on projectile hit). Inert when duration is 0. */
  readonly debuff: StatusKind
  /** 0 means this kind inflicts nothing — `applyStatus` becomes a no-op. */
  readonly debuffDuration: number
}

const spec = (s: EnemySpec): EnemySpec => s

export const ENEMY_SPECS: Record<EnemyKind, EnemySpec> = {
  rusher: spec({
    name: 'Rusher', cost: 10, hp: 14, speed: 170, radius: 9,
    contactDamage: 6, xp: 4, move: 'chase',
    projDamage: 0, projSpeed: 0, fireRange: 0, fireCooldown: 0, keepDistance: 0,
    detonates: false, blastRadius: 0, blastDamage: 0, spawnEvery: 0,
    spawnKind: 'rusher', splitCount: 0,
    debuff: 'slow', debuffDuration: 0,
  }),
  stalker: spec({
    name: 'Stalker', cost: 24, hp: 20, speed: 110, radius: 10,
    contactDamage: 4, xp: 8, move: 'skirmish',
    projDamage: 7, projSpeed: 260, fireRange: 250, fireCooldown: 1.6, keepDistance: 200,
    detonates: false, blastRadius: 0, blastDamage: 0, spawnEvery: 0,
    spawnKind: 'rusher', splitCount: 0,
    debuff: 'slow', debuffDuration: 0,
  }),
  tank: spec({
    name: 'Tank', cost: 45, hp: 120, speed: 55, radius: 18,
    contactDamage: 14, xp: 20, move: 'chase',
    projDamage: 0, projSpeed: 0, fireRange: 0, fireCooldown: 0, keepDistance: 0,
    detonates: false, blastRadius: 0, blastDamage: 0, spawnEvery: 0,
    spawnKind: 'rusher', splitCount: 0,
    debuff: 'slow', debuffDuration: 0,
  }),
  bomber: spec({
    name: 'Bomber', cost: 30, hp: 16, speed: 140, radius: 10,
    contactDamage: 0, xp: 10, move: 'chase',
    projDamage: 0, projSpeed: 0, fireRange: 0, fireCooldown: 0, keepDistance: 0,
    detonates: true, blastRadius: 70, blastDamage: 22, spawnEvery: 0,
    spawnKind: 'rusher', splitCount: 0,
    debuff: 'slow', debuffDuration: 0,
  }),
  splitter: spec({
    name: 'Splitter', cost: 34, hp: 30, speed: 95, radius: 13,
    contactDamage: 5, xp: 12, move: 'chase',
    projDamage: 0, projSpeed: 0, fireRange: 0, fireCooldown: 0, keepDistance: 0,
    detonates: false, blastRadius: 0, blastDamage: 0, spawnEvery: 0,
    spawnKind: 'rusher', splitCount: 3,
    debuff: 'slow', debuffDuration: 0,
  }),
  artillery: spec({
    name: 'Artillery', cost: 52, hp: 26, speed: 70, radius: 12,
    contactDamage: 0, xp: 16, move: 'skirmish',
    projDamage: 13, projSpeed: 190, fireRange: 460, fireCooldown: 2.6, keepDistance: 420,
    detonates: false, blastRadius: 0, blastDamage: 0, spawnEvery: 0,
    spawnKind: 'rusher', splitCount: 0,
    debuff: 'suppress', debuffDuration: 2.5,
  }),
  warden: spec({
    name: 'Warden', cost: 40, hp: 34, speed: 215, radius: 8,
    contactDamage: 7, xp: 14, move: 'chase',
    projDamage: 0, projSpeed: 0, fireRange: 0, fireCooldown: 0, keepDistance: 0,
    detonates: false, blastRadius: 0, blastDamage: 0, spawnEvery: 0,
    spawnKind: 'rusher', splitCount: 0,
    debuff: 'slow', debuffDuration: 2.0,
  }),
  colossus: spec({
    name: 'Colossus', cost: 150, hp: 700, speed: 40, radius: 34,
    contactDamage: 30, xp: 80, move: 'chase',
    projDamage: 0, projSpeed: 0, fireRange: 0, fireCooldown: 0, keepDistance: 0,
    detonates: false, blastRadius: 0, blastDamage: 0, spawnEvery: 0,
    spawnKind: 'rusher', splitCount: 0,
    debuff: 'slow', debuffDuration: 0,
  }),
  hivemind: spec({
    name: 'Hivemind', cost: 220, hp: 420, speed: 60, radius: 28,
    contactDamage: 10, xp: 100, move: 'chase',
    projDamage: 0, projSpeed: 0, fireRange: 0, fireCooldown: 0, keepDistance: 0,
    detonates: false, blastRadius: 0, blastDamage: 0, spawnEvery: 2.5,
    spawnKind: 'rusher', splitCount: 0,
    debuff: 'slow', debuffDuration: 0,
  }),
  leech: spec({
    name: 'Leech', cost: 190, hp: 500, speed: 75, radius: 30,
    contactDamage: 12, xp: 90, move: 'chase',
    projDamage: 0, projSpeed: 0, fireRange: 0, fireCooldown: 0, keepDistance: 0,
    detonates: false, blastRadius: 0, blastDamage: 0, spawnEvery: 0,
    spawnKind: 'rusher', splitCount: 0,
    debuff: 'bleed', debuffDuration: 3.5,
  }),
} as const

export const UNIT_ORDER: readonly [UnitKind, ...UnitKind[]] = [
  'rusher', 'stalker', 'tank', 'bomber', 'splitter', 'artillery', 'warden',
]
export const BOSS_ORDER: readonly [BossKind, ...BossKind[]] = ['colossus', 'hivemind', 'leech']
export const BOSS_UNLOCK_AT: Record<BossKind, number> = {
  colossus: 60, hivemind: 120, leech: 180,
}
export const BOSS_COOLDOWN: Record<BossKind, number> = {
  colossus: 25, hivemind: 30, leech: 28,
}
