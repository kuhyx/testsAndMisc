/**
 * The simulation's vocabulary: arena constants, difficulty tiers, the director's
 * powers, and the shape of the game state itself.
 *
 * The enemy roster lives in `enemies.ts` and the status effects in
 * `statusKinds.ts`; both are imported here and re-exported by neither, so
 * consumers name the module that owns what they use.
 */

import type { Rng } from './rng'
import type { Vec } from './vec'
import type { BossKind, EnemyKind, UnitKind } from './enemies'
import type { StatusKind } from './statusKinds'

export const ARENA = { w: 960, h: 600 } as const
export const GAME_DURATION = 300
export const CONTACT_COOLDOWN = 0.5
export const ENERGY_CAP = 400
export const ENERGY_START = 30

export type DifficultyId = 'haunting' | 'normal' | 'crusade'

export interface DifficultyConfig {
  readonly label: string
  readonly enemyHp: number
  readonly enemySpeed: number
  readonly survivorHp: number
  readonly energyRate: number
  readonly duration: number
}

/** `normal` is exactly 1 across the board, so it is the identity tier. */
export const DIFFICULTIES: Record<DifficultyId, DifficultyConfig> = {
  haunting: {
    label: 'Haunting',
    enemyHp: 0.85, enemySpeed: 0.95, survivorHp: 1.25, energyRate: 1.25, duration: 240,
  },
  normal: {
    label: 'Normal',
    enemyHp: 1, enemySpeed: 1, survivorHp: 1, energyRate: 1, duration: GAME_DURATION,
  },
  crusade: {
    label: 'Crusade',
    enemyHp: 1.2, enemySpeed: 1.05, survivorHp: 0.85, energyRate: 0.85, duration: 360,
  },
}
export const DIFFICULTY_ORDER: readonly [DifficultyId, ...DifficultyId[]] = [
  'haunting', 'normal', 'crusade',
]

export type PowerKind = 'ambush' | 'frenzy' | 'rift'
export const POWER_ORDER: readonly [PowerKind, ...PowerKind[]] = ['ambush', 'frenzy', 'rift']
export const POWER_NAMES: Record<PowerKind, string> = {
  ambush: 'Ambush', frenzy: 'Frenzy', rift: 'Rift',
}
/** Ambush additionally costs the summoned unit's own price. */
export const POWER_COST: Record<PowerKind, number> = { ambush: 45, frenzy: 90, rift: 25 }
export const POWER_COOLDOWN: Record<PowerKind, number> = { ambush: 8, frenzy: 45, rift: 12 }

/** How close to the survivor an ambush lands. Just outside its contact ring. */
export const AMBUSH_RADIUS = 130
/** ~137.5deg. Irrational share of a turn, so repeated steps never land twice. */
export const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))
export const FRENZY_DURATION = 6
export const FRENZY_SPEED = 1.35
export const FRENZY_DAMAGE = 1.3
export const RIFT_DURATION = 10

/** Arena edge, as a finite union so `Record` indexing stays non-optional. */
export type EdgeId = 0 | 1 | 2 | 3
export const EDGE_ORDER: readonly [EdgeId, ...EdgeId[]] = [0, 1, 2, 3]
export const EDGE_NAMES: Record<EdgeId, string> = {
  0: 'North', 1: 'South', 2: 'West', 3: 'East',
}

export type UpgradeId = 'damage' | 'fireRate' | 'speed' | 'vitality' | 'regen' | 'multishot'
export const UPGRADE_POOL: readonly [UpgradeId, ...UpgradeId[]] = [
  'damage', 'fireRate', 'speed', 'vitality', 'regen', 'multishot',
]

export interface Survivor {
  pos: Vec
  hp: number
  maxHp: number
  speed: number
  regen: number
  damage: number
  multishot: number
  fireCooldown: number
  fireTimer: number
  level: number
  xp: number
  xpNext: number
  kills: number
  /** Seconds remaining per status. A finite-union Record, so indexing stays `number`. */
  statuses: Record<StatusKind, number>
}

export interface Enemy {
  id: number
  kind: EnemyKind
  pos: Vec
  hp: number
  hitTimer: number
  fireTimer: number
  spawnTimer: number
}

export interface Projectile {
  id: number
  from: 'survivor' | 'enemy'
  pos: Vec
  vel: Vec
  radius: number
  damage: number
  ttl: number
  /** Carried on the shot itself so a hit needs no lookup of a possibly-dead firer. */
  debuff: StatusKind
  debuffDuration: number
}

export interface DirectorState {
  energy: number
  waveIndex: number
  bossCooldowns: Record<BossKind, number>
  powerCooldowns: Record<PowerKind, number>
  frenzyTimer: number
  riftTimer: number
  riftEdge: EdgeId
  /** Rotates ambush placement deterministically, without drawing from the RNG. */
  ambushIndex: number
}

export type DirectorAction =
  | { type: 'spawn'; kind: UnitKind }
  | { type: 'wave' }
  | { type: 'boss'; kind: BossKind }
  | { type: 'ambush'; kind: UnitKind }
  | { type: 'frenzy' }
  | { type: 'rift'; edge: EdgeId }

export type Status = 'running' | 'directorWon' | 'survivorWon'

export interface GameState {
  status: Status
  difficulty: DifficultyConfig
  t: number
  duration: number
  rng: Rng
  survivor: Survivor
  enemies: Enemy[]
  projectiles: Projectile[]
  director: DirectorState
  upgrades: UpgradeId[]
  nextId: number
  outcomeTime: number
}
