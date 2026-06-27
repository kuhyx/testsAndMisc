import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PuzzleResult } from "./PuzzleResult";
import type { FallingPuzzleItem, PuzzlePiece } from "../types";

const makePiece = (row: number, col: number): PuzzlePiece => ({
  row,
  col,
  gridSize: 2,
  imageUrl: `data:image/png;base64,${row}-${col}`,
  pieceWidth: 50,
  pieceHeight: 50,
});

const makeFalling = (row: number, col: number): FallingPuzzleItem => ({
  kind: "puzzle",
  id: `${row}-${col}`,
  piece: makePiece(row, col),
  x: 0,
  y: 0,
  speed: 3,
  startFrame: 0,
  status: "caught",
});

describe("PuzzleResult", () => {
  it("renders grade A and percentage for 75% completion", () => {
    // gridSize=2 → total=4; 3 caught → 75% → A
    render(
      <PuzzleResult
        result={{
          gridSize: 2,
          caughtPieces: [
            makeFalling(0, 0),
            makeFalling(0, 1),
            makeFalling(1, 0),
          ],
          missedPieces: [makeFalling(1, 1)],
        }}
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText(/3 \/ 4 pieces caught/)).toBeInTheDocument();
  });

  it("renders grade S at 100%", () => {
    render(
      <PuzzleResult
        result={{
          gridSize: 1,
          caughtPieces: [makeFalling(0, 0)],
          missedPieces: [],
        }}
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("S")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("renders grade B at exactly 50%", () => {
    render(
      <PuzzleResult
        result={{
          gridSize: 2,
          caughtPieces: [makeFalling(0, 0), makeFalling(0, 1)],
          missedPieces: [makeFalling(1, 0), makeFalling(1, 1)],
        }}
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
  });

  it("renders grade C at 25%", () => {
    render(
      <PuzzleResult
        result={{
          gridSize: 2,
          caughtPieces: [makeFalling(0, 0)],
          missedPieces: [
            makeFalling(0, 1),
            makeFalling(1, 0),
            makeFalling(1, 1),
          ],
        }}
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("C")).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
  });

  it("renders grade D at 0%", () => {
    render(
      <PuzzleResult
        result={{
          gridSize: 2,
          caughtPieces: [],
          missedPieces: [
            makeFalling(0, 0),
            makeFalling(0, 1),
            makeFalling(1, 0),
            makeFalling(1, 1),
          ],
        }}
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("D")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("renders img elements for caught pieces and div holes for missed", () => {
    const { container } = render(
      <PuzzleResult
        result={{
          gridSize: 2,
          caughtPieces: [makeFalling(0, 0), makeFalling(1, 1)],
          missedPieces: [makeFalling(0, 1), makeFalling(1, 0)],
        }}
        onRestart={() => undefined}
      />,
    );
    // 2 img elements for caught pieces
    const imgs = container.querySelectorAll("img");
    expect(imgs).toHaveLength(2);
    // The grid div has inline style with gridTemplateColumns; its non-img children are holes
    const gridEl = container.querySelector(
      '[style*="repeat"]',
    ) as HTMLElement;
    const holeDivs = Array.from(gridEl.children).filter(
      (c) => c.tagName === "DIV",
    );
    expect(holeDivs).toHaveLength(2);
  });

  it("img src matches imageUrl of caught piece", () => {
    render(
      <PuzzleResult
        result={{
          gridSize: 1,
          caughtPieces: [makeFalling(0, 0)],
          missedPieces: [],
        }}
        onRestart={() => undefined}
      />,
    );
    const img = screen.getByRole("img", { name: "Piece 0-0" });
    expect(img).toHaveAttribute("src", "data:image/png;base64,0-0");
  });

  it("calls onRestart when Play again is clicked", () => {
    const onRestart = vi.fn();
    render(
      <PuzzleResult
        result={{ gridSize: 1, caughtPieces: [], missedPieces: [] }}
        onRestart={onRestart}
      />,
    );
    fireEvent.click(screen.getByText("Play again"));
    expect(onRestart).toHaveBeenCalledOnce();
  });

  it("handles gridSize=0 without errors (0% fallback)", () => {
    render(
      <PuzzleResult
        result={{ gridSize: 0, caughtPieces: [], missedPieces: [] }}
        onRestart={() => undefined}
      />,
    );
    expect(screen.getByText("D")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });
});
