import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DropZone } from "./DropZone";

const makeFile = (name: string, type = "text/plain"): File =>
  new File(["x"], name, { type });

describe("DropZone", () => {
  it("renders title and subtitle", () => {
    render(<DropZone onFiles={() => undefined} onPuzzle={() => undefined} />);
    expect(screen.getByText("Bucket Catch")).toBeInTheDocument();
    expect(
      screen.getByText(/Drop your files here/),
    ).toBeInTheDocument();
  });

  it("shows initial grid equation", () => {
    render(<DropZone onFiles={() => undefined} onPuzzle={() => undefined} />);
    expect(screen.getByText("4×4 = 16 pieces")).toBeInTheDocument();
  });

  it("dragOver adds dragging class; dragLeave removes it", () => {
    const { container } = render(
      <DropZone onFiles={() => undefined} onPuzzle={() => undefined} />,
    );
    const zone = container.firstChild as HTMLElement;
    expect(zone.className).not.toContain("dragging");
    fireEvent.dragOver(zone);
    expect(zone.className).toContain("dragging");
    fireEvent.dragLeave(zone);
    expect(zone.className).not.toContain("dragging");
  });

  it("drop with files calls onFiles and shows count (plural)", () => {
    const onFiles = vi.fn();
    const { container } = render(
      <DropZone onFiles={onFiles} onPuzzle={() => undefined} />,
    );
    const zone = container.firstChild as HTMLElement;
    const f1 = makeFile("a.txt");
    const f2 = makeFile("b.txt");
    fireEvent.drop(zone, { dataTransfer: { files: [f1, f2] } });
    expect(onFiles).toHaveBeenCalledWith([f1, f2]);
    expect(screen.getByText("2 files ready")).toBeInTheDocument();
  });

  it("drop with files shows singular count for 1 file", () => {
    const { container } = render(
      <DropZone onFiles={() => undefined} onPuzzle={() => undefined} />,
    );
    const zone = container.firstChild as HTMLElement;
    fireEvent.drop(zone, { dataTransfer: { files: [makeFile("a.txt")] } });
    expect(screen.getByText("1 file ready")).toBeInTheDocument();
  });

  it("drop with empty files does not call onFiles", () => {
    const onFiles = vi.fn();
    const { container } = render(
      <DropZone onFiles={onFiles} onPuzzle={() => undefined} />,
    );
    const zone = container.firstChild as HTMLElement;
    fireEvent.drop(zone, { dataTransfer: { files: [] } });
    expect(onFiles).not.toHaveBeenCalled();
  });

  it("file input change with files calls onFiles", () => {
    const onFiles = vi.fn();
    const { container } = render(
      <DropZone onFiles={onFiles} onPuzzle={() => undefined} />,
    );
    const fileInput = container.querySelector(
      "input[type='file'][multiple]",
    ) as HTMLInputElement;
    const file = makeFile("c.txt");
    Object.defineProperty(fileInput, "files", {
      value: [file],
      configurable: true,
    });
    fireEvent.change(fileInput);
    expect(onFiles).toHaveBeenCalledWith([file]);
  });

  it("file input change with empty files does not call onFiles", () => {
    const onFiles = vi.fn();
    const { container } = render(
      <DropZone onFiles={onFiles} onPuzzle={() => undefined} />,
    );
    const fileInput = container.querySelector(
      "input[type='file'][multiple]",
    ) as HTMLInputElement;
    Object.defineProperty(fileInput, "files", {
      value: [],
      configurable: true,
    });
    fireEvent.change(fileInput);
    expect(onFiles).not.toHaveBeenCalled();
  });

  it("file input change with null files (nullish-coalesce branch) does not call onFiles", () => {
    const onFiles = vi.fn();
    const { container } = render(
      <DropZone onFiles={onFiles} onPuzzle={() => undefined} />,
    );
    const fileInput = container.querySelector(
      "input[type='file'][multiple]",
    ) as HTMLInputElement;
    Object.defineProperty(fileInput, "files", {
      value: null,
      configurable: true,
    });
    fireEvent.change(fileInput);
    expect(onFiles).not.toHaveBeenCalled();
  });

  it("puzzle input change with file calls onPuzzle with current gridSize", () => {
    const onPuzzle = vi.fn();
    const { container } = render(
      <DropZone onFiles={() => undefined} onPuzzle={onPuzzle} />,
    );
    const puzzleInput = container.querySelector(
      "input[accept='image/*']",
    ) as HTMLInputElement;
    const imgFile = makeFile("photo.png", "image/png");
    Object.defineProperty(puzzleInput, "files", {
      value: [imgFile],
      configurable: true,
    });
    fireEvent.change(puzzleInput);
    expect(onPuzzle).toHaveBeenCalledWith(imgFile, 4); // default gridSize = 4
  });

  it("puzzle input change with null files does not call onPuzzle (optional-chain null branch)", () => {
    const onPuzzle = vi.fn();
    const { container } = render(
      <DropZone onFiles={() => undefined} onPuzzle={onPuzzle} />,
    );
    const puzzleInput = container.querySelector(
      "input[accept='image/*']",
    ) as HTMLInputElement;
    Object.defineProperty(puzzleInput, "files", {
      value: null,
      configurable: true,
    });
    fireEvent.change(puzzleInput);
    expect(onPuzzle).not.toHaveBeenCalled();
  });

  it("puzzle input change with empty files does not call onPuzzle (no first element)", () => {
    const onPuzzle = vi.fn();
    const { container } = render(
      <DropZone onFiles={() => undefined} onPuzzle={onPuzzle} />,
    );
    const puzzleInput = container.querySelector(
      "input[accept='image/*']",
    ) as HTMLInputElement;
    Object.defineProperty(puzzleInput, "files", {
      value: [],
      configurable: true,
    });
    fireEvent.change(puzzleInput);
    expect(onPuzzle).not.toHaveBeenCalled();
  });

  it("Play Puzzle Mode button triggers click on hidden puzzle input", () => {
    const { container } = render(
      <DropZone onFiles={() => undefined} onPuzzle={() => undefined} />,
    );
    const puzzleInput = container.querySelector(
      "input[accept='image/*']",
    ) as HTMLInputElement;
    const clickSpy = vi.spyOn(puzzleInput, "click").mockImplementation(
      () => undefined,
    );
    fireEvent.click(screen.getByText(/Play Puzzle Mode/));
    expect(clickSpy).toHaveBeenCalled();
  });

  it("clicking preset updates gridSize display and equation", () => {
    render(<DropZone onFiles={() => undefined} onPuzzle={() => undefined} />);
    fireEvent.click(screen.getByText("2×2"));
    expect(screen.getByText("2×2 = 4 pieces")).toBeInTheDocument();
  });

  it("custom grid input with valid value updates gridSize", () => {
    render(<DropZone onFiles={() => undefined} onPuzzle={() => undefined} />);
    const input = screen.getByLabelText("Custom grid size");
    fireEvent.change(input, { target: { value: "7" } });
    expect(screen.getByText("7×7 = 49 pieces")).toBeInTheDocument();
  });

  it("custom grid input with NaN value does not update gridSize", () => {
    render(<DropZone onFiles={() => undefined} onPuzzle={() => undefined} />);
    const input = screen.getByLabelText("Custom grid size");
    fireEvent.change(input, { target: { value: "xyz" } });
    expect(screen.getByText("4×4 = 16 pieces")).toBeInTheDocument();
  });

  it("custom grid input with value below 2 does not update gridSize", () => {
    render(<DropZone onFiles={() => undefined} onPuzzle={() => undefined} />);
    const input = screen.getByLabelText("Custom grid size");
    fireEvent.change(input, { target: { value: "1" } });
    expect(screen.getByText("4×4 = 16 pieces")).toBeInTheDocument();
  });

  it("onPuzzle uses updated gridSize after preset click", () => {
    const onPuzzle = vi.fn();
    const { container } = render(
      <DropZone onFiles={() => undefined} onPuzzle={onPuzzle} />,
    );
    fireEvent.click(screen.getByText("3×3")); // change gridSize to 3
    const puzzleInput = container.querySelector(
      "input[accept='image/*']",
    ) as HTMLInputElement;
    const imgFile = makeFile("img.png", "image/png");
    Object.defineProperty(puzzleInput, "files", {
      value: [imgFile],
      configurable: true,
    });
    fireEvent.change(puzzleInput);
    expect(onPuzzle).toHaveBeenCalledWith(imgFile, 3);
  });
});
