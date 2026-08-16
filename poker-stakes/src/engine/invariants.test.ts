import { describe, expect, it } from 'vitest'
import { legalActions } from './bettingRound'
import { startInteractiveHand } from './interactiveHand'
import { createRng } from './rng'
import { applyHandResult, cashOutSession, deriveBlindSize, startSession } from './session'
import { settleSession } from '../stakes/settlement'

const BUY_IN_CHIPS = 100
const SEEDS = 40
const MAX_HANDS = 400
const POLICY_SEED_SALT = 0x9e3779b9

/**
 * Property sweep over many seeds, complementing the scripted per-module tests: those pin specific
 * scenarios, this asserts the properties that must hold for EVERY session the engine can produce.
 *
 * Chip conservation is the important one — a heads-up table is a closed system, so if chips are
 * ever created or destroyed the stakes model is compromised (the settlement formula reads
 * `finalChips` directly, so invented chips would become forgiven debt).
 */
describe('engine invariants across many seeds', () => {
  it('conserves chips, keeps stacks non-negative, and always settles by the formula', () => {
    const failures: string[] = []
    let totalDecisions = 0
    let sessionsEnded = 0

    for (let seed = 1; seed <= SEEDS; seed += 1) {
      let session = startSession({ buyInChips: BUY_IN_CHIPS })
      const dealRng = createRng(seed)
      const policyRng = createRng(seed ^ POLICY_SEED_SALT)
      const tableTotal = session.stacks.player + session.stacks.opponent

      for (let hand = 0; hand < MAX_HANDS && session.outcome === null; hand += 1) {
        const { bigBlind, smallBlind } = deriveBlindSize(BUY_IN_CHIPS)
        const interactive = startInteractiveHand(
          dealRng,
          policyRng,
          { buttonSeat: session.buttonSeat, bigBlind, smallBlind, stacks: session.stacks },
          50,
        )

        // Always take the first legal action — an arbitrary but deterministic strategy. The
        // invariants below must hold regardless of how badly the player plays.
        let guard = 0
        while (interactive.status.kind === 'awaiting' && guard < 200) {
          const [first] = legalActions(interactive.status.step.betting)
          if (first === undefined) {
            break
          }
          interactive.submit(first)
          totalDecisions += 1
          guard += 1
        }

        const status = interactive.status
        if (status.kind !== 'complete') {
          failures.push(`seed ${String(seed)} hand ${String(hand)}: hand never completed`)
          break
        }

        session = applyHandResult(session, status.result)
        const sum = session.stacks.player + session.stacks.opponent
        if (sum !== tableTotal) {
          failures.push(`seed ${String(seed)} hand ${String(hand)}: chips ${String(sum)} != ${String(tableTotal)}`)
        }
        if (session.stacks.player < 0 || session.stacks.opponent < 0) {
          failures.push(`seed ${String(seed)} hand ${String(hand)}: negative stack`)
        }
      }

      if (session.outcome !== null) {
        sessionsEnded += 1
      }
      const ended = session.outcome !== null ? session : cashOutSession(session)
      const { outcome } = ended
      if (outcome !== null) {
        const debt = settleSession({ taskTypeId: 'pushups', chips: BUY_IN_CHIPS }, outcome, 'id', 0)
        const expected = Math.max(0, 2 * BUY_IN_CHIPS - outcome.finalChips)
        if (debt.owedUnits !== expected) {
          failures.push(`seed ${String(seed)}: owed ${String(debt.owedUnits)} != ${String(expected)}`)
        }
        if (debt.owedUnits > 2 * BUY_IN_CHIPS) {
          failures.push(`seed ${String(seed)}: owed ${String(debt.owedUnits)} exceeds the 2x cap`)
        }
      }
    }

    // Guards against the sweep silently doing nothing (an empty loop would otherwise "pass").
    expect(totalDecisions).toBeGreaterThan(500)
    expect(sessionsEnded).toBe(SEEDS)
    expect(failures.slice(0, 10)).toEqual([])
  })
})
