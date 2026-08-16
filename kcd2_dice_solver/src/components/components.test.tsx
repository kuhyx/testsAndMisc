/**
 * Component tests for the three ways of entering an inventory: clicking a die,
 * scrolling the wheel over its counter, and fuzzy-searching by name.
 */

import { fireEvent, render, screen, } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { highlightName } from "./DieRow.tsx";
import { QuantityStepper, clampCount } from "./QuantityStepper.tsx";

/**
 * Apply the updater a component emitted, to assert on the resulting count.
 *
 * @param mock - The mocked onChange.
 * @param previous - The count it should be applied to.
 * @param call - Which call to read, counting from the end by default.
 * @returns The count the component asked for.
 */
function applied(
  mock: { mock: { calls: unknown[][] } },
  previous: number,
  call = mock.mock.calls.length - 1,
): number {
  const update = mock.mock.calls[call][0] as (p: number) => number;
  return update(previous);
}


describe("clampCount", () => {
  it("keeps a value inside the range", () => {
    expect(clampCount(3, 6)).toBe(3);
    expect(clampCount(-2, 6)).toBe(0);
    expect(clampCount(99, 6)).toBe(6);
  });

  it("floors fractions and rejects nonsense", () => {
    expect(clampCount(2.9, 6)).toBe(2);
    expect(clampCount(Number.NaN, 6)).toBe(0);
  });
});

describe("QuantityStepper", () => {
  it("adds one when the plus button is pressed", async () => {
    const onChange = vi.fn();
    render(<QuantityStepper label="Ordinary die" value={2} max={6} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Add one Ordinary die"));
    expect(applied(onChange, 2)).toBe(3);
  });

  it("removes one when the minus button is pressed", async () => {
    const onChange = vi.fn();
    render(<QuantityStepper label="Ordinary die" value={2} max={6} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Remove one Ordinary die"));
    expect(applied(onChange, 2)).toBe(1);
  });

  it("disables the buttons at the ends of the range", () => {
    const { rerender } = render(
      <QuantityStepper label="Ordinary die" value={0} max={6} onChange={vi.fn()} />,
    );
    expect(screen.getByLabelText("Remove one Ordinary die")).toBeDisabled();
    rerender(<QuantityStepper label="Ordinary die" value={6} max={6} onChange={vi.fn()} />);
    expect(screen.getByLabelText("Add one Ordinary die")).toBeDisabled();
  });

  it("increments on a wheel scroll up and decrements on a scroll down", () => {
    const onChange = vi.fn();
    const { container } = render(
      <QuantityStepper label="Ordinary die" value={2} max={6} onChange={onChange} />,
    );
    const stepper = container.querySelector(".stepper");
    if (!stepper) {
      throw new Error("no stepper");
    }
    fireEvent.wheel(stepper, { deltaY: -120 });
    expect(applied(onChange, 2)).toBe(3);
    fireEvent.wheel(stepper, { deltaY: 120 });
    expect(applied(onChange, 2)).toBe(1);
  });

  it("accumulates a burst of wheel ticks rather than collapsing them", () => {
    // Wheel events arrive far faster than React re-renders. Emitting an
    // absolute `value + 1` made six ticks land as one; each emitted updater
    // must therefore compose.
    const onChange = vi.fn();
    const { container } = render(
      <QuantityStepper label="Ordinary die" value={0} max={6} onChange={onChange} />,
    );
    const stepper = container.querySelector(".stepper");
    if (!stepper) {
      throw new Error("no stepper");
    }
    for (let i = 0; i < 6; i += 1) {
      fireEvent.wheel(stepper, { deltaY: -120 });
    }
    expect(onChange).toHaveBeenCalledTimes(6);
    const total = onChange.mock.calls.reduce(
      (count: number, [update]) => (update as (p: number) => number)(count),
      0,
    );
    expect(total).toBe(6);
  });

  it("shows the count as a readout inside the stepper", () => {
    // The wheel handler lives on `.stepper`, so the readout must stay a direct
    // child of it — App.test.tsx reaches the wheel target via parentElement.
    render(<QuantityStepper label="Ordinary die" value={3} max={6} onChange={vi.fn()} />);
    const readout = screen.getByLabelText("How many Ordinary die");
    expect(readout).toHaveTextContent("3");
    expect(readout.parentElement).toHaveClass("stepper");
  });
});

describe("highlightName", () => {
  it("marks the matched characters and leaves the rest alone", () => {
    const { container } = render(<p>{highlightName("Die", [0])}</p>);
    expect(container.querySelectorAll("mark")).toHaveLength(1);
    expect(container.textContent).toBe("Die");
  });
});
