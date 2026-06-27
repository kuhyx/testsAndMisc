import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { FileGameResult, PuzzleGameResult, TransferMode } from "./types";
import App from "./App";

// ---- Minimal component mocks ------------------------------------------------

vi.mock("./components/DropZone", () => ({
  DropZone: ({
    onFiles,
    onPuzzle,
  }: {
    onFiles: (f: File[]) => void;
    onPuzzle: (f: File, g: number) => void;
  }) => (
    <div data-testid="dropzone">
      <button
        onClick={() => { onFiles([new File(["x"], "a.txt")]); }}
      >
        drop-files
      </button>
      <button
        onClick={() => {
          onPuzzle(new File(["x"], "img.png", { type: "image/png" }), 3);
        }}
      >
        drop-puzzle
      </button>
    </div>
  ),
}));

vi.mock("./components/ModeSelect", () => ({
  ModeSelect: ({
    onStart,
  }: {
    onStart: (m: TransferMode, g?: number) => void;
  }) => (
    <div data-testid="modeselect">
      <button onClick={() => { onStart("download"); }}>mode-download</button>
      <button onClick={() => { onStart("upload"); }}>mode-upload</button>
      <button onClick={() => { onStart("puzzle", 3); }}>mode-puzzle</button>
    </div>
  ),
}));

vi.mock("./components/GameCanvas", () => ({
  GameCanvas: ({ onDone }: { onDone: (r: FileGameResult) => void }) => (
    <button
      onClick={() => { onDone({ caught: [], missed: [] }); }}
    >
      game-done
    </button>
  ),
}));

vi.mock("./components/PuzzleCanvas", () => ({
  PuzzleCanvas: ({
    onDone,
  }: {
    onDone: (r: PuzzleGameResult) => void;
  }) => (
    <button
      onClick={() => {
        onDone({ caughtPieces: [], missedPieces: [], gridSize: 3 });
      }}
    >
      puzzle-done
    </button>
  ),
}));

vi.mock("./components/ScoreScreen", () => ({
  ScoreScreen: ({ onRestart }: { onRestart: () => void }) => (
    <button onClick={onRestart}>score-restart</button>
  ),
}));

vi.mock("./components/PuzzleResult", () => ({
  PuzzleResult: ({ onRestart }: { onRestart: () => void }) => (
    <button onClick={onRestart}>puzzle-restart</button>
  ),
}));

// ---- Tests ------------------------------------------------------------------

describe("App", () => {
  it("initially renders DropZone (drop phase)", () => {
    render(<App />);
    expect(screen.getByTestId("dropzone")).toBeInTheDocument();
  });

  it("handleFiles transitions from drop to mode phase", () => {
    render(<App />);
    fireEvent.click(screen.getByText("drop-files"));
    expect(screen.getByTestId("modeselect")).toBeInTheDocument();
  });

  it("handlePuzzleDirect skips mode phase and goes straight to PuzzleCanvas", () => {
    render(<App />);
    fireEvent.click(screen.getByText("drop-puzzle"));
    expect(screen.getByText("puzzle-done")).toBeInTheDocument();
  });

  it("handleStart('download') transitions from mode to GameCanvas", () => {
    render(<App />);
    fireEvent.click(screen.getByText("drop-files"));
    fireEvent.click(screen.getByText("mode-download"));
    expect(screen.getByText("game-done")).toBeInTheDocument();
  });

  it("handleStart('upload') transitions from mode to GameCanvas", () => {
    render(<App />);
    fireEvent.click(screen.getByText("drop-files"));
    fireEvent.click(screen.getByText("mode-upload"));
    expect(screen.getByText("game-done")).toBeInTheDocument();
  });

  it("handleStart('puzzle', gridSize) sets puzzleGridSize and shows PuzzleCanvas", () => {
    render(<App />);
    fireEvent.click(screen.getByText("drop-files"));
    fireEvent.click(screen.getByText("mode-puzzle"));
    expect(screen.getByText("puzzle-done")).toBeInTheDocument();
  });

  it("handleFileDone transitions to done phase showing ScoreScreen", () => {
    render(<App />);
    fireEvent.click(screen.getByText("drop-files"));
    fireEvent.click(screen.getByText("mode-download"));
    fireEvent.click(screen.getByText("game-done"));
    expect(screen.getByText("score-restart")).toBeInTheDocument();
  });

  it("handlePuzzleDone transitions to done phase showing PuzzleResult", () => {
    render(<App />);
    fireEvent.click(screen.getByText("drop-puzzle"));
    fireEvent.click(screen.getByText("puzzle-done"));
    expect(screen.getByText("puzzle-restart")).toBeInTheDocument();
  });

  it("handleRestart from ScoreScreen resets to drop phase", () => {
    render(<App />);
    fireEvent.click(screen.getByText("drop-files"));
    fireEvent.click(screen.getByText("mode-download"));
    fireEvent.click(screen.getByText("game-done"));
    fireEvent.click(screen.getByText("score-restart"));
    expect(screen.getByTestId("dropzone")).toBeInTheDocument();
  });

  it("handleRestart from PuzzleResult resets to drop phase", () => {
    render(<App />);
    fireEvent.click(screen.getByText("drop-puzzle"));
    fireEvent.click(screen.getByText("puzzle-done"));
    fireEvent.click(screen.getByText("puzzle-restart"));
    expect(screen.getByTestId("dropzone")).toBeInTheDocument();
  });
});
