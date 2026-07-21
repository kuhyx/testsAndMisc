/**
 * The searchable list of every die in the game, with owned quantities.
 */

import type { JSX } from "react";
import { DICE } from "../data/dice.ts";
import { fuzzyFilter } from "../lib/fuzzy.ts";
import { DieRow } from "./DieRow.tsx";
import type { CountUpdater } from "./QuantityStepper.tsx";

export interface DiceListProps {
  readonly query: string;
  readonly counts: Readonly<Record<string, number>>;
  readonly onChange: (id: string, update: CountUpdater) => void;
}

/**
 * Fuzzy-filtered list of dice.
 *
 * @param props - The search query, current counts, and a change handler.
 * @returns The list element, or an empty-state message.
 */
export function DiceList({ query, counts, onChange }: DiceListProps): JSX.Element {
  const matches = fuzzyFilter(query, DICE, (die) => die.name);

  if (matches.length === 0) {
    return <p className="empty">No die matches “{query}”.</p>;
  }

  return (
    <ul className="die-list">
      {matches.map(({ item, indices }) => (
        <DieRow
          key={item.id}
          die={item}
          count={counts[item.id] ?? 0}
          highlight={indices}
          onChange={(update) => {
            onChange(item.id, update);
          }}
        />
      ))}
    </ul>
  );
}
