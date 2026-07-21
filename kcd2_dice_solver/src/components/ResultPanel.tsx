/**
 * The recommendation: six dice, the numbers behind them, and a badge per tier.
 */

import type { JSX } from "react";
import type { Die } from "../data/dice.ts";
import type { SolveResponse } from "../core/solve.ts";

export interface ResultPanelProps {
  readonly result: SolveResponse | null;
  readonly error: string | null;
  readonly solving: boolean;
}

/**
 * Collapse a loadout into "3x Weighted die, 2x Pie die" form.
 *
 * @param dice - The six dice of a loadout.
 * @returns One entry per distinct die, in descending count order.
 */
export function summariseDice(dice: readonly Die[]): { die: Die; count: number }[] {
  const byId = new Map<string, { die: Die; count: number }>();
  for (const die of dice) {
    const existing = byId.get(die.id);
    if (existing) {
      existing.count += 1;
    } else {
      byId.set(die.id, { die, count: 1 });
    }
  }
  return [...byId.values()].sort((a, b) => b.count - a.count);
}

/**
 * Format a point figure for display.
 *
 * @param value - The number of points.
 * @returns The value rounded to whole points with thousands separators.
 */
function points(value: number): string {
  return Math.round(value).toLocaleString("en-GB");
}

/**
 * The recommendation panel.
 *
 * @param props - The latest solve, any error, and whether one is in flight.
 * @returns The panel element.
 */
export function ResultPanel({ result, error, solving }: ResultPanelProps): JSX.Element {
  if (error) {
    return (
      <div className="result">
        <p className="empty">{error}</p>
      </div>
    );
  }
  if (!result) {
    return (
      <div className="result">
        <p className="empty">
          {solving ? "Solving…" : "Add at least six dice to get a recommendation."}
        </p>
      </div>
    );
  }

  return (
    <div className={solving ? "result stale" : "result"}>
      <h2>Best loadout</h2>
      <ul className="loadout">
        {summariseDice(result.dice).map(({ die, count }) => (
          <li key={die.id}>
            <span className="loadout-count">{count}×</span>
            <span className="loadout-name">{die.name}</span>
          </li>
        ))}
      </ul>

      <dl className="stats">
        <div>
          <dt>Expected score per throw</dt>
          <dd>{points(result.evaluation.ev)}</dd>
        </div>
        <div>
          <dt>Bust chance</dt>
          <dd>{(result.evaluation.bustProbability * 100).toFixed(2)}%</dd>
        </div>
        <div>
          <dt>Good throw (90th pct)</dt>
          <dd>{points(result.evaluation.p90)}</dd>
        </div>
        <div>
          <dt>Simulated points per turn</dt>
          <dd>
            {points(result.simulation.meanPerTurn)}
            <small> ± {result.simulation.standardError.toFixed(1)}</small>
          </dd>
        </div>
      </dl>

      <p className="provenance">
        {result.optimal
          ? "Provably optimal: every possible loadout was evaluated."
          : "Best found by local search — near-optimal, not proven."}{" "}
        Chosen from {result.inventorySize} dice.
      </p>

      {result.alternatives.length > 0 && (
        <details className="alternatives">
          <summary>Runners-up</summary>
          <ul>
            {result.alternatives.map((alternative, index) => (
              // Alternatives are a fixed ranked list; the index is their rank.
              <li key={index}>
                <span className="alt-ev">{points(alternative.evaluation.ev)}</span>
                {summariseDice(alternative.dice)
                  .map(({ die, count }) => `${count}× ${die.name}`)
                  .join(", ")}
              </li>
            ))}
          </ul>
        </details>
      )}

      <h2>Best badge per tier</h2>
      {result.badges.length === 0 ? (
        <p className="empty">Tick the badges you own to have them ranked.</p>
      ) : (
        result.badges.map((recommendation) => {
          const [best, ...rest] = recommendation.ranked;
          return (
            <section key={recommendation.tier} className="badge-result">
              <h3 className={`tier tier-${recommendation.tier}`}>{recommendation.tier}</h3>
              <p className="badge-pick">
                <strong>{best.badge.name}</strong>
                {best.pointsPerGame !== null && (
                  <span className="badge-value"> ~{points(best.pointsPerGame)} pts/game</span>
                )}
              </p>
              <p className="badge-reason">{best.reason}</p>
              {best.dice && (
                <p className="badge-reason">
                  With this badge, bring:{" "}
                  {summariseDice(best.dice)
                    .map(({ die, count }) => `${count}× ${die.name}`)
                    .join(", ")}
                </p>
              )}
              {rest.length > 0 && (
                <details>
                  <summary>Other {recommendation.tier} badges</summary>
                  <ul>
                    {rest.map((valuation) => (
                      <li key={valuation.badge.id}>
                        {valuation.badge.name}
                        {valuation.pointsPerGame === null
                          ? " — situational"
                          : ` — ~${points(valuation.pointsPerGame)} pts/game`}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </section>
          );
        })
      )}
    </div>
  );
}
