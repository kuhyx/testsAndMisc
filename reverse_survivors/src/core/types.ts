import type { Rng } from './rng'
import type { Vec } from './vec'

export const ARENA = { w: 960, h: 600 } as const
export const GAME_DURATION = 300
export const CONTACT_COOLDOWN = 0.5
export const ENERGY_CAP = 400
export const ENERGY_START = 30

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
