/**
 * The quantity control for one inventory row.
 *
 * Two ways to change a count: the −/+ buttons and the mouse wheel. There used
 * to be a third — typing into a number input — but the inventory list now packs
 * 43 dice into one screen, and the input cost 28px of a ~155px cell at phone
 * width. With a maximum of six, three taps of "+" covers the whole range, so
 * the field bought nothing that justified the space.
 */

import type { JSX } from "react";

/**
 * How a count changes: a function of the previous count, never an absolute
 * value computed from a stale render. Wheel events and rapid clicks arrive
 * faster than React re-renders, so `onChange(value + 1)` silently collapses a
 * burst of six into one — which is exactly what happened the first time this
 * was driven in a real browser.
 */
export type CountUpdater = (previous: number) => number;

export interface QuantityStepperProps {
  readonly label: string;
  readonly value: number;
  readonly max: number;
  readonly onChange: (update: CountUpdater) => void;
}

/**
 * Clamp a count into the allowed range, treating anything unparsable as zero.
 *
 * The `Number.isFinite` guard is defensive since the number input was removed —
 * every caller now passes `previous + delta`, which cannot be NaN. It is kept
 * because the inventory importer also clamps values that came from a file.
 *
 * @param value - Proposed count.
 * @param max - Largest allowed count.
 * @returns The clamped whole number.
 */
export function clampCount(value: number, max: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.min(max, Math.max(0, Math.floor(value)));
}

/**
 * Stepper for how many of a die or badge the player owns.
 *
 * @param props - Current value, bounds, and the change handler.
 * @returns The stepper element.
 */
export function QuantityStepper({
  label,
  value,
  max,
  onChange,
}: QuantityStepperProps): JSX.Element {
  const step = (delta: number): void => {
    onChange((previous) => clampCount(previous + delta, max));
  };

  return (
    <div
      className="stepper"
      onWheel={(event) => {
        // Scrolling up adds one, down removes one. The row is not scrollable
        // itself, so nothing is stolen from the page.
        event.preventDefault();
        step(event.deltaY < 0 ? 1 : -1);
      }}
    >
      <button
        type="button"
        className="stepper-button stepper-remove"
        aria-label={`Remove one ${label}`}
        disabled={value === 0}
        onClick={() => {
          step(-1);
        }}
      >
        −
      </button>
      {/*
       * `output` rather than a span: it has an implicit `status` role and is a
       * nameable element, so `aria-label` actually resolves for screen readers
       * (on a bare span most of them ignore it). It stays a direct child of
       * `.stepper` so the wheel handler still covers it.
       */}
      <output className="stepper-value" aria-label={`How many ${label}`}>
        {value}
      </output>
      <button
        type="button"
        className="stepper-button stepper-add"
        aria-label={`Add one ${label}`}
        disabled={value >= max}
        onClick={() => {
          step(1);
        }}
      >
        +
      </button>
    </div>
  );
}
