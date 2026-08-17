/**
 * The simulation tick: build a game state, then advance it.
 *
 * The per-actor work lives in three modules with a one-way import graph —
 * `simUnit` (shared geometry and enemy construction) is the leaf, `simSurvivor`
 * builds on it, and `simThreats` builds on both. This file is the only place
 * that reaches into all three, and the only place the director's actions are
 * applied.
 */

import { applyAction, tickDirector } from './director'
import { createRng } from './rng'
import type { DifficultyId, DirectorAction, GameState } from './types'
import { DIFFICULTIES, ENERGY_START } from './types'
import { createSurvivor, survivorStep } from './simSurvivor'
import { enemiesStep, projectilesStep } from './simThreats'

export const createInitialState = (
  seed: number,
  duration?: number,
  difficulty: DifficultyId = 'normal',
): GameState => {
  const cfg = DIFFICULTIES[difficulty]
  return {
    status: 'running',
    difficulty: cfg,
    t: 0,
    duration: duration ?? cfg.duration,
    rng: createRng(seed),
    survivor: createSurvivor(cfg),
    enemies: [],
    projectiles: [],
    director: {
      energy: ENERGY_START,
      waveIndex: 0,
      bossCooldowns: { colossus: 0, hivemind: 0, leech: 0 },
      powerCooldowns: { ambush: 0, frenzy: 0, rift: 0 },
      frenzyTimer: 0,
      riftTimer: 0,
      riftEdge: 0,
      ambushIndex: 0,
    },
    upgrades: [],
    nextId: 1,
    outcomeTime: 0,
  }
}

export const step = (state: GameState, actions: readonly DirectorAction[], dt: number): void => {
  if (state.status !== 'running') {
    return
  }
  state.t += dt
  tickDirector(state, dt)
  for (const action of actions) {
    applyAction(state, action)
  }
  survivorStep(state, dt)
  enemiesStep(state, dt)
  projectilesStep(state, dt)
  state.enemies = state.enemies.filter((e) => e.hp > 0)
  if (state.survivor.hp <= 0) {
    state.status = 'directorWon'
    state.outcomeTime = state.t
  } else if (state.t >= state.duration) {
    state.status = 'survivorWon'
    state.outcomeTime = state.t
  }
}
