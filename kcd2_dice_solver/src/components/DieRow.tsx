/**
 * One die in the inventory list: name, face distribution, and a quantity.
 */

import type { JSX } from "react";
import type { Die } from "../data/dice.ts";
import { QuantityStepper } from "./QuantityStepper.tsx";
import type { CountUpdater } from "./QuantityStepper.tsx";

/** Most of any single die the game lets you carry into one match. */
export const MAX_PER_DIE = 6;

export interface DieRowProps {
  readonly die: Die;
  readonly count: number;
  readonly highlight: readonly number[];
  readonly onChange: (update: CountUpdater) => void;
}

/**
 * Render a name with the fuzzy-matched characters marked.
 *
 * Adjacent characters are grouped into runs rather than emitted one element per
 * character: it keeps the DOM small and, more usefully, leaves the unmatched
 * parts of the name as whole text nodes.
 *
 * @param name - The die's display name.
 * @param highlight - Indices in the name that the search query matched.
 * @returns The name as alternating plain and marked runs.
 */
export function highlightName(name: string, highlight: readonly number[]): JSX.Element {
  const marked = new Set(highlight);
  const runs: { text: string; hit: boolean }[] = [];
  for (let index = 0; index < name.length; index += 1) {
    const hit = marked.has(index);
    const last = runs.at(-1);
    if (last?.hit === hit) {
      last.text += name[index];
    } else {
      runs.push({ text: name[index], hit });
    }
  }
  return (
    <>
      {runs.map((run, index) =>
        run.hit ? (
          // Index keys are correct here: the runs come from a fixed string.
          <mark key={index}>{run.text}</mark>
        ) : (
          <span key={index}>{run.text}</span>
        ),
      )}
    </>
  );
}

/**
 * A single inventory row. Clicking anywhere on the row adds one die.
 *
 * @param props - The die, its current count, search highlights, and a handler.
 * @returns The row element.
 */
export function DieRow({ die, count, highlight, onChange }: DieRowProps): JSX.Element {
  const isWild = die.wildcardFaces.length > 0;
  return (
    <li className={count > 0 ? "die-row owned" : "die-row"}>
      <button
        type="button"
        className="die-main"
        title={die.description}
        // The stepper's "+" already owns "Add one <die>"; this control needs a
        // distinct accessible name so the two are not ambiguous.
        aria-label={die.name}
        onClick={() => {
          onChange((previous) => Math.min(MAX_PER_DIE, previous + 1));
        }}
      >
        <span className="die-name">{highlightName(die.name, highlight)}</span>
        <span className="die-faces">
          {die.weights.map((weight, face) => (
            <span
              className="die-face"
              key={face}
              title={`${face + 1}: ${(weight * 100).toFixed(1)}%`}
            >
              <span className="die-face-bar" style={{ height: `${weight * 100 * 1.6}%` }} />
              <span className="die-face-label">{face + 1}</span>
            </span>
          ))}
        </span>
        {isWild && <span className="die-tag">wild</span>}
      </button>
      <QuantityStepper label={die.name} value={count} max={MAX_PER_DIE} onChange={onChange} />
    </li>
  );
}
