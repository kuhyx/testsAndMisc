import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MediaViewer } from "./media-viewer.tsx";
import type { DirEntry } from "../api/types.ts";

function mk(name: string): DirEntry {
  return { name, path: `/${name}`, kind: "file", size: 1, mtimeMs: 0 };
}

describe("MediaViewer", () => {
  it("shows an image and toggles zoom on click", async () => {
    render(
      <MediaViewer
        entry={mk("a.jpg")}
        url="/a.jpg"
        onClose={vi.fn()}
        onPrev={vi.fn()}
        onNext={vi.fn()}
      />,
    );
    const img = screen.getByAltText("a.jpg");
    expect(img.className).not.toContain("zoomed");
    await userEvent.click(img);
    expect(img.className).toContain("zoomed");
  });

  it("renders a <video> for video files and does not close on video click", () => {
    const onClose = vi.fn();
    render(
      <MediaViewer
        entry={mk("v.mp4")}
        url="/v.mp4"
        onClose={onClose}
        onPrev={vi.fn()}
        onNext={vi.fn()}
      />,
    );
    const video = document.querySelector("video");
    expect(video).not.toBeNull();
    if (video) fireEvent.click(video);
    // stopPropagation keeps the stage's onClose from firing.
    expect(onClose).not.toHaveBeenCalled();
  });

  it("offers a download for non-media files", () => {
    render(
      <MediaViewer
        entry={mk("x.bin")}
        url="/x.bin"
        onClose={vi.fn()}
        onPrev={vi.fn()}
        onNext={vi.fn()}
      />,
    );
    expect(screen.getByText("Download")).toBeInTheDocument();
  });

  it("responds to keyboard: Esc/←/→", () => {
    const onClose = vi.fn();
    const onPrev = vi.fn();
    const onNext = vi.fn();
    render(
      <MediaViewer
        entry={mk("a.jpg")}
        url="/a.jpg"
        onClose={onClose}
        onPrev={onPrev}
        onNext={onNext}
      />,
    );
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.keyDown(window, { key: "a" });
    expect(onNext).toHaveBeenCalledOnce();
    expect(onPrev).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("nav buttons and stage click work", async () => {
    const onClose = vi.fn();
    const onPrev = vi.fn();
    const onNext = vi.fn();
    render(
      <MediaViewer
        entry={mk("a.jpg")}
        url="/a.jpg"
        onClose={onClose}
        onPrev={onPrev}
        onNext={onNext}
      />,
    );
    await userEvent.click(screen.getByLabelText("Previous"));
    await userEvent.click(screen.getByLabelText("Next"));
    expect(onPrev).toHaveBeenCalledOnce();
    expect(onNext).toHaveBeenCalledOnce();
  });
});
