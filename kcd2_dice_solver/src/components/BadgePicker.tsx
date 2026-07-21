/**
 * Badge ownership, grouped by tier.
 *
 * Badges are owned or not owned — there is no quantity — so these are toggles
 * rather than steppers. They are grouped by tier because that is the axis the
 * recommendation is reported on: a badge only takes effect when your opponent
 * brings one of the same tier, and you cannot know theirs in advance.
 */

import type { JSX } from "react";
import { BADGES, TIERS } from "../data/badges.ts";
import { fuzzyFilter } from "../lib/fuzzy.ts";

export interface BadgePickerProps {
  readonly query: string;
  readonly owned: ReadonlySet<string>;
  readonly onToggle: (id: string, owned: boolean) => void;
}

/**
 * Tier-grouped badge checkboxes, filtered by the same fuzzy search.
 *
 * @param props - Query, owned ids, and a toggle handler.
 * @returns The picker element.
 */
export function BadgePicker({ query, owned, onToggle }: BadgePickerProps): JSX.Element {
  const matches = fuzzyFilter(query, BADGES, (badge) => badge.name).map((m) => m.item);
  const matched = new Set(matches.map((badge) => badge.id));

  return (
    <div className="badge-picker">
      {TIERS.map((tier) => {
        const inTier = BADGES.filter(
          (badge) => badge.tier === tier && matched.has(badge.id),
        );
        if (inTier.length === 0) {
          return null;
        }
        return (
          <section key={tier}>
            <h3 className={`tier tier-${tier}`}>{tier}</h3>
            <ul className="badge-list">
              {inTier.map((badge) => (
                <li key={badge.id}>
                  <label title={badge.description}>
                    <input
                      type="checkbox"
                      checked={owned.has(badge.id)}
                      onChange={(event) => {
                        onToggle(badge.id, event.target.checked);
                      }}
                    />
                    <span>{badge.name}</span>
                  </label>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
