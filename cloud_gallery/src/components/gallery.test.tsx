import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Gallery } from "./gallery.tsx";
import type { DufsClient } from "../api/dufs-client.ts";
import type { DirEntry } from "../api/types.ts";

function entry(name: string, kind: "dir" | "file"): DirEntry {
  return { name, path: `/${name}`, kind, size: 10, mtimeMs: 0 };
}

function makeClient(overrides: Partial<DufsClient> = {}): DufsClient {
  return {
    list: vi.fn(() =>
      Promise.resolve([
        entry("Media", "dir"),
        entry("pic.jpg", "file"),
        entry("clip.mp4", "file"),
        entry("notes.txt", "file"),
      ]),
    ),
    fileUrl: (p: string) => p,
    thumbUrl: (p: string) => `/.thumbs${p}.jpg`,
    upload: vi.fn(() => Promise.resolve()),
    remove: vi.fn(() => Promise.resolve()),
    readText: vi.fn(() => Promise.resolve("hello world")),
    writeText: vi.fn(() => Promise.resolve()),
    ...overrides,
  };
}

beforeEach(() => {
  window.location.hash = "";
});

describe("Gallery", () => {
  it("renders a directory listing", async () => {
    render(<Gallery client={makeClient()} />);
    expect(await screen.findByText("Media")).toBeInTheDocument();
    expect(screen.getByText("pic.jpg")).toBeInTheDocument();
    expect(screen.getByText("clip.mp4")).toBeInTheDocument();
  });

  it("opens an image in the viewer and closes it", async () => {
    render(<Gallery client={makeClient()} />);
    await userEvent.click(await screen.findByText("pic.jpg"));
    await waitFor(() => {
      expect(document.querySelector(".viewer-img")).not.toBeNull();
    });
    await userEvent.click(screen.getByLabelText("Close"));
    await waitFor(() => {
      expect(document.querySelector(".viewer-img")).toBeNull();
    });
  });

  it("plays a video in the viewer", async () => {
    render(<Gallery client={makeClient()} />);
    await userEvent.click(await screen.findByText("clip.mp4"));
    await waitFor(() => {
      expect(document.querySelector("video")).not.toBeNull();
    });
  });

  it("edits a text file and saves it", async () => {
    const client = makeClient();
    render(<Gallery client={client} />);
    await userEvent.click(await screen.findByText("notes.txt"));
    const area = await screen.findByDisplayValue("hello world");
    await userEvent.clear(area);
    await userEvent.type(area, "new text");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(client.writeText).toHaveBeenCalledWith("/notes.txt", "new text");
    });
  });

  it("deletes a file after confirming", async () => {
    const client = makeClient();
    render(<Gallery client={client} />);
    await screen.findByText("pic.jpg");
    await userEvent.click(screen.getByLabelText("Delete pic.jpg"));
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => {
      expect(client.remove).toHaveBeenCalledWith("/pic.jpg");
    });
  });

  it("uploads picked files", async () => {
    const client = makeClient();
    const { container } = render(<Gallery client={client} />);
    await screen.findByText("pic.jpg");
    const input = container.querySelector<HTMLInputElement>(
      'input[type="file"]',
    );
    expect(input).not.toBeNull();
    const file = new File(["x"], "up.png", { type: "image/png" });
    if (input) fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(client.upload).toHaveBeenCalled();
    });
  });

  it("navigates between media in the viewer", async () => {
    render(<Gallery client={makeClient()} />);
    await userEvent.click(await screen.findByText("pic.jpg"));
    await waitFor(() => {
      expect(document.querySelector(".viewer-img")).not.toBeNull();
    });
    fireEvent.keyDown(window, { key: "ArrowRight" });
    await waitFor(() => {
      expect(document.querySelector("video")).not.toBeNull();
    });
  });

  it("surfaces an upload error", async () => {
    const client = makeClient({
      upload: vi.fn(() => Promise.reject(new Error("uperr"))),
    });
    const { container } = render(<Gallery client={client} />);
    await screen.findByText("pic.jpg");
    const input = container.querySelector<HTMLInputElement>(
      'input[type="file"]',
    );
    if (input) {
      fireEvent.change(input, {
        target: { files: [new File(["x"], "u.png")] },
      });
    }
    expect(await screen.findByText(/uperr/)).toBeInTheDocument();
  });

  it("surfaces a delete error", async () => {
    const client = makeClient({
      remove: vi.fn(() => Promise.reject(new Error("delerr"))),
    });
    render(<Gallery client={client} />);
    await screen.findByText("pic.jpg");
    await userEvent.click(screen.getByLabelText("Delete pic.jpg"));
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(await screen.findByText(/delerr/)).toBeInTheDocument();
  });

  it("cancels a delete", async () => {
    const client = makeClient();
    render(<Gallery client={client} />);
    await screen.findByText("pic.jpg");
    await userEvent.click(screen.getByLabelText("Delete pic.jpg"));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(client.remove).not.toHaveBeenCalled();
  });

  it("shows an error when listing fails", async () => {
    const client = makeClient({
      list: vi.fn(() => Promise.reject(new Error("boom"))),
    });
    render(<Gallery client={client} />);
    expect(await screen.findByText(/boom/)).toBeInTheDocument();
  });
});
