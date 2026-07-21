/**
 * The quantity control for one inventory row.
 *
 * Three ways to change a count, because all three were asked for: the −/+
 * buttons, typing a number, and scrolling the mouse wheel over the control.
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
        className="stepper-button"
        aria-label={`Remove one ${label}`}
        disabled={value === 0}
        onClick={() => {
          step(-1);
        }}
      >
        −
      </button>
      <input
        className="stepper-value"
        type="number"
        min={0}
        max={max}
        value={value}
        aria-label={`How many ${label}`}
        onChange={(event) => {
          // Typing is the one case that really is an absolute value.
          const typed = Number(event.target.value);
          onChange(() => clampCount(typed, max));
        }}
      />
      <button
        type="button"
        className="stepper-button"
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
