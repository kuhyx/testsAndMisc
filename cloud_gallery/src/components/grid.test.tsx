import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Grid } from "./grid.tsx";
import type { DufsClient } from "../api/dufs-client.ts";
import type { DirEntry } from "../api/types.ts";

function entry(name: string, kind: "dir" | "file"): DirEntry {
  return { name, path: `/${name}`, kind, size: 42, mtimeMs: 0 };
}

function makeClient(): DufsClient {
  return {
    list: vi.fn(),
    fileUrl: (p: string) => p,
    thumbUrl: (p: string) => `/.thumbs${p}.jpg`,
    upload: vi.fn(),
    remove: vi.fn(),
    readText: vi.fn(),
    writeText: vi.fn(),
  };
}

const entries: DirEntry[] = [
  entry("Media", "dir"),
  entry("pic.jpg", "file"),
  entry("clip.mp4", "file"),
  entry("notes.txt", "file"),
  entry("data.bin", "file"),
];

function renderGrid(over: Partial<Parameters<typeof Grid>[0]> = {}) {
  const props = {
    client: makeClient(),
    entries,
    onOpenDir: vi.fn(),
    onOpenMedia: vi.fn(),
    onEditText: vi.fn(),
    onDelete: vi.fn(),
    ...over,
  };
  render(<Grid {...props} />);
  return props;
}

describe("Grid", () => {
  it("activates dir, media and text entries via their tiles", async () => {
    const onOpenDir = vi.fn();
    const onOpenMedia = vi.fn();
    const onEditText = vi.fn();
    renderGrid({ onOpenDir, onOpenMedia, onEditText });
    await userEvent.click(screen.getByText("Media"));
    await userEvent.click(screen.getByText("pic.jpg"));
    await userEvent.click(screen.getByText("notes.txt"));
    // Non-media, non-text file does nothing on activate.
    await userEvent.click(screen.getByText("data.bin"));
    expect(onOpenDir).toHaveBeenCalledWith("/Media");
    expect(onOpenMedia).toHaveBeenCalledWith(entries[1]);
    expect(onEditText).toHaveBeenCalledWith(entries[3]);
  });

  it("renders a download link and a delete button for files", async () => {
    const onDelete = vi.fn();
    renderGrid({ onDelete });
    const download = screen.getByLabelText("Download pic.jpg");
    expect(download).toHaveAttribute("href", "/pic.jpg");
    await userEvent.click(screen.getByLabelText("Delete pic.jpg"));
    expect(onDelete).toHaveBeenCalledWith(entries[1]);
  });

  it("falls back to an icon when a thumbnail fails to load", () => {
    renderGrid();
    // Image thumbnail breaks -> picture fallback glyph.
    fireEvent.error(screen.getByAltText("pic.jpg"));
    expect(screen.getByText("🖼")).toBeInTheDocument();
    // Video thumbnail breaks -> film fallback glyph.
    fireEvent.error(screen.getByAltText("clip.mp4"));
    expect(screen.getByText("🎞")).toBeInTheDocument();
  });
});
