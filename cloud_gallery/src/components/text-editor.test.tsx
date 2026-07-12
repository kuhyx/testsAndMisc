import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TextEditor } from "./text-editor.tsx";
import type { DufsClient } from "../api/dufs-client.ts";
import type { DirEntry } from "../api/types.ts";

const entry: DirEntry = {
  name: "n.txt",
  path: "/n.txt",
  kind: "file",
  size: 3,
  mtimeMs: 0,
};

function client(over: Partial<DufsClient>): DufsClient {
  return {
    list: vi.fn(),
    fileUrl: (p) => p,
    thumbUrl: (p) => p,
    upload: vi.fn(),
    remove: vi.fn(),
    readText: vi.fn(() => Promise.resolve("body")),
    writeText: vi.fn(() => Promise.resolve()),
    ...over,
  };
}

describe("TextEditor", () => {
  it("loads, edits and saves", async () => {
    const c = client({});
    render(<TextEditor client={c} entry={entry} onClose={vi.fn()} />);
    const area = await screen.findByDisplayValue("body");
    await userEvent.clear(area);
    await userEvent.type(area, "changed");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(c.writeText).toHaveBeenCalledWith("/n.txt", "changed");
    });
    expect(await screen.findByText("Saved")).toBeInTheDocument();
  });

  it("shows a load error", async () => {
    const c = client({ readText: vi.fn(() => Promise.reject(new Error("nope"))) });
    render(<TextEditor client={c} entry={entry} onClose={vi.fn()} />);
    expect(await screen.findByText("nope")).toBeInTheDocument();
  });

  it("shows a save error", async () => {
    const c = client({
      writeText: vi.fn(() => Promise.reject(new Error("wfail"))),
    });
    render(<TextEditor client={c} entry={entry} onClose={vi.fn()} />);
    await screen.findByDisplayValue("body");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("wfail")).toBeInTheDocument();
  });

  it("stringifies a non-Error load rejection", async () => {
    const c = client({
      // eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors
      readText: vi.fn(() => Promise.reject("plain-load-failure")),
    });
    render(<TextEditor client={c} entry={entry} onClose={vi.fn()} />);
    expect(await screen.findByText("plain-load-failure")).toBeInTheDocument();
  });

  it("stringifies a non-Error save rejection", async () => {
    const c = client({
      // eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors
      writeText: vi.fn(() => Promise.reject("plain-save-failure")),
    });
    render(<TextEditor client={c} entry={entry} onClose={vi.fn()} />);
    await screen.findByDisplayValue("body");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("plain-save-failure")).toBeInTheDocument();
  });

  it("closes", async () => {
    const onClose = vi.fn();
    render(<TextEditor client={client({})} entry={entry} onClose={onClose} />);
    await screen.findByDisplayValue("body");
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("ignores a load that resolves after unmount", async () => {
    let settle: (v: string) => void = () => undefined;
    const pending = new Promise<string>((resolve) => {
      settle = resolve;
    });
    const c = client({ readText: vi.fn(() => pending) });
    const { unmount } = render(
      <TextEditor client={c} entry={entry} onClose={vi.fn()} />,
    );
    unmount();
    await act(async () => {
      settle("late");
      await pending;
    });
  });

  it("ignores a load that rejects after unmount", async () => {
    let fail: (e: unknown) => void = () => undefined;
    const pending = new Promise<string>((_, reject) => {
      fail = reject;
    });
    const c = client({ readText: vi.fn(() => pending) });
    const { unmount } = render(
      <TextEditor client={c} entry={entry} onClose={vi.fn()} />,
    );
    unmount();
    await act(async () => {
      fail(new Error("late"));
      await pending.catch(() => undefined);
    });
  });
});
