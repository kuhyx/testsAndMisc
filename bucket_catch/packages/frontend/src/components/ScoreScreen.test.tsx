import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ScoreScreen } from "./ScoreScreen";

vi.mock("../lib/zipDownload", () => ({
  zipDownload: vi.fn(),
}));
vi.mock("../lib/uploadFiles", () => ({
  uploadFiles: vi.fn(),
}));

import { zipDownload } from "../lib/zipDownload";
import { uploadFiles } from "../lib/uploadFiles";

const makeFile = (name: string, size = 10): File => {
  const f = new File(["x".repeat(size)], name, { type: "text/plain" });
  return f;
};

const result1 = {
  caught: [makeFile("a.txt"), makeFile("b.txt")],
  missed: [makeFile("c.txt")],
};

describe("ScoreScreen", () => {
  beforeEach(() => {
    vi.mocked(zipDownload).mockResolvedValue(undefined);
    vi.mocked(uploadFiles).mockResolvedValue([]);
  });

  it("renders grade, percentage, and file lists", () => {
    render(
      <ScoreScreen result={result1} mode="download" onRestart={() => undefined} />,
    );
    // 2 caught / 3 total = 67% → grade B
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("67%")).toBeInTheDocument();
    expect(screen.getByText("Caught")).toBeInTheDocument();
    expect(screen.getByText("Missed")).toBeInTheDocument();
  });

  it("shows download button for download mode with multiple files", async () => {
    render(
      <ScoreScreen result={result1} mode="download" onRestart={() => undefined} />,
    );
    expect(
      screen.getByText(/Download 2 caught files/),
    ).toBeInTheDocument();
  });

  it("shows singular 'file' for exactly 1 caught file", () => {
    render(
      <ScoreScreen
        result={{ caught: [makeFile("x.txt")], missed: [] }}
        mode="download"
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText(/Download 1 caught file$/)).toBeInTheDocument();
  });

  it("triggers zip download and shows done state", async () => {
    render(
      <ScoreScreen result={result1} mode="download" onRestart={() => undefined} />,
    );
    fireEvent.click(screen.getByText(/Download/));
    await waitFor(() => {
      expect(screen.getByText("Downloaded!")).toBeInTheDocument();
    });
    expect(zipDownload).toHaveBeenCalledWith(result1.caught);
  });

  it("shows upload button for upload mode", () => {
    render(
      <ScoreScreen result={result1} mode="upload" onRestart={() => undefined} />,
    );
    expect(screen.getByText(/Upload 2 caught files to server/)).toBeInTheDocument();
  });

  it("shows singular upload text for exactly 1 caught file", () => {
    render(
      <ScoreScreen
        result={{ caught: [makeFile("x.txt")], missed: [] }}
        mode="upload"
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText(/Upload 1 caught file to server$/)).toBeInTheDocument();
  });

  it("triggers upload and shows done state", async () => {
    render(
      <ScoreScreen result={result1} mode="upload" onRestart={() => undefined} />,
    );
    fireEvent.click(screen.getByText(/Upload/));
    await waitFor(() => {
      expect(screen.getByText("Uploaded to server!")).toBeInTheDocument();
    });
    expect(uploadFiles).toHaveBeenCalledWith(result1.caught);
  });

  it("shows error state when action throws an Error", async () => {
    vi.mocked(zipDownload).mockRejectedValue(new Error("Network error"));
    render(
      <ScoreScreen result={result1} mode="download" onRestart={() => undefined} />,
    );
    fireEvent.click(screen.getByText(/Download/));
    await waitFor(() => {
      expect(screen.getByText(/Error: Network error/)).toBeInTheDocument();
    });
  });

  it("shows error state when action throws a non-Error value", async () => {
    vi.mocked(uploadFiles).mockRejectedValue("server unavailable");
    render(
      <ScoreScreen result={result1} mode="upload" onRestart={() => undefined} />,
    );
    fireEvent.click(screen.getByText(/Upload/));
    await waitFor(() => {
      expect(screen.getByText(/Error: server unavailable/)).toBeInTheDocument();
    });
  });

  it("calls onRestart when play again is clicked", () => {
    const onRestart = vi.fn();
    render(
      <ScoreScreen
        result={{ caught: [], missed: [] }}
        mode="download"
        onRestart={onRestart}
      />,
    );
    fireEvent.click(screen.getByText("Play again"));
    expect(onRestart).toHaveBeenCalledOnce();
  });

  it("hides action button when no files were caught", () => {
    render(
      <ScoreScreen
        result={{ caught: [], missed: [makeFile("x.txt")] }}
        mode="download"
        onRestart={() => undefined}
      />,
    );
    expect(screen.queryByText(/Download/)).not.toBeInTheDocument();
  });

  it("grades S at >= 90%", () => {
    const files = Array.from({ length: 10 }, (_, i) => makeFile(`f${i}.txt`));
    render(
      <ScoreScreen
        result={{ caught: files.slice(0, 9), missed: files.slice(9) }}
        mode="download"
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("S")).toBeInTheDocument();
  });

  it("grades A at >= 75%", () => {
    const files = Array.from({ length: 4 }, (_, i) => makeFile(`f${i}.txt`));
    render(
      <ScoreScreen
        result={{ caught: files.slice(0, 3), missed: files.slice(3) }}
        mode="download"
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("grades C at >= 25%", () => {
    const files = Array.from({ length: 4 }, (_, i) => makeFile(`f${i}.txt`));
    render(
      <ScoreScreen
        result={{ caught: files.slice(0, 1), missed: files.slice(1) }}
        mode="download"
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("C")).toBeInTheDocument();
  });

  it("grades D below 25%", () => {
    const files = Array.from({ length: 5 }, (_, i) => makeFile(`f${i}.txt`));
    render(
      <ScoreScreen
        result={{ caught: [], missed: files }}
        mode="download"
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("D")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("handles zero total files (0%)", () => {
    render(
      <ScoreScreen
        result={{ caught: [], missed: [] }}
        mode="download"
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("D")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });
});
