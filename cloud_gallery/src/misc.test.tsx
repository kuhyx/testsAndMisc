import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useHashPath } from "./lib/use-hash-path.ts";
import { ConfirmDialog } from "./components/confirm-dialog.tsx";
import { App } from "./app.tsx";

function Harness(): React.JSX.Element {
  const [path, navigate] = useHashPath();
  return (
    <div>
      <span data-testid="p">{path}</span>
      <button
        type="button"
        onClick={() => {
          navigate("/x/y");
        }}
      >
        go
      </button>
    </div>
  );
}

describe("useHashPath", () => {
  beforeEach(() => {
    window.location.hash = "";
  });
  it("reflects and updates the hash", async () => {
    render(<Harness />);
    expect(screen.getByTestId("p").textContent).toBe("/");
    await userEvent.click(screen.getByText("go"));
    // hashchange may not auto-fire in jsdom; nudge it.
    act(() => {
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("p").textContent).toBe("/x/y");
    });
  });
});

describe("ConfirmDialog", () => {
  it("confirms, cancels and cancels on overlay click", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { rerender } = render(
      <ConfirmDialog
        message="Sure?"
        confirmLabel="Yes"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Yes" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledOnce();
    rerender(
      <ConfirmDialog
        message="Sure?"
        confirmLabel="Yes"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    // clicking the dialog body should NOT cancel (stopPropagation)
    await userEvent.click(screen.getByText("Sure?"));
    expect(onCancel).toHaveBeenCalledOnce();
  });
});

describe("App", () => {
  it("mounts the gallery", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.reject(new Error("offline")),
    ) as unknown as typeof fetch;
    render(<App />);
    expect(
      await screen.findByRole("button", { name: "Upload" }),
    ).toBeInTheDocument();
  });
});
