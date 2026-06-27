import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ModeSelect } from "./ModeSelect";

const makeFile = (name: string, type = "text/plain"): File =>
  new File(["x"], name, { type });

const makeImageFile = (): File =>
  new File(["x"], "photo.png", { type: "image/png" });

describe("ModeSelect", () => {
  it("renders singular file count for 1 file", () => {
    render(
      <ModeSelect files={[makeFile("a.txt")]} onStart={() => undefined} />,
    );
    expect(screen.getByText("1 file ready to drop")).toBeInTheDocument();
  });

  it("renders plural file count for multiple files", () => {
    render(
      <ModeSelect
        files={[makeFile("a.txt"), makeFile("b.txt")]}
        onStart={() => undefined}
      />,
    );
    expect(screen.getByText("2 files ready to drop")).toBeInTheDocument();
  });

  it("calls onStart('download') when Download is clicked", () => {
    const onStart = vi.fn();
    render(<ModeSelect files={[makeFile("a.txt")]} onStart={onStart} />);
    fireEvent.click(screen.getByText("Download"));
    expect(onStart).toHaveBeenCalledWith("download");
  });

  it("calls onStart('upload') when Upload is clicked", () => {
    const onStart = vi.fn();
    render(<ModeSelect files={[makeFile("a.txt")]} onStart={onStart} />);
    fireEvent.click(screen.getByText("Upload"));
    expect(onStart).toHaveBeenCalledWith("upload");
  });

  it("shows disabled puzzle message when files is not a single image", () => {
    render(
      <ModeSelect
        files={[makeFile("a.txt"), makeFile("b.txt")]}
        onStart={() => undefined}
      />,
    );
    expect(
      screen.getByText("Drop exactly one image file to play puzzle mode."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Start")).not.toBeInTheDocument();
  });

  it("shows disabled puzzle message for single non-image file", () => {
    render(
      <ModeSelect files={[makeFile("a.txt")]} onStart={() => undefined} />,
    );
    expect(
      screen.getByText("Drop exactly one image file to play puzzle mode."),
    ).toBeInTheDocument();
  });

  it("shows puzzle controls when a single image file is loaded", () => {
    render(
      <ModeSelect files={[makeImageFile()]} onStart={() => undefined} />,
    );
    expect(
      screen.getByText("Catch puzzle pieces to assemble your image!"),
    ).toBeInTheDocument();
    expect(screen.getByText("Start")).toBeInTheDocument();
  });

  it("clicking a preset button updates grid size display", () => {
    render(
      <ModeSelect files={[makeImageFile()]} onStart={() => undefined} />,
    );
    expect(screen.getByText("4×4 = 16 pieces")).toBeInTheDocument();
    fireEvent.click(screen.getByText("3×3"));
    expect(screen.getByText("3×3 = 9 pieces")).toBeInTheDocument();
  });

  it("custom grid input with valid value updates grid size", () => {
    render(
      <ModeSelect files={[makeImageFile()]} onStart={() => undefined} />,
    );
    const input = screen.getByLabelText("Custom grid size");
    fireEvent.change(input, { target: { value: "6" } });
    expect(screen.getByText("6×6 = 36 pieces")).toBeInTheDocument();
  });

  it("custom grid input with NaN value does not update grid size", () => {
    render(
      <ModeSelect files={[makeImageFile()]} onStart={() => undefined} />,
    );
    const input = screen.getByLabelText("Custom grid size");
    fireEvent.change(input, { target: { value: "abc" } });
    expect(screen.getByText("4×4 = 16 pieces")).toBeInTheDocument();
  });

  it("custom grid input with value < 2 does not update grid size", () => {
    render(
      <ModeSelect files={[makeImageFile()]} onStart={() => undefined} />,
    );
    const input = screen.getByLabelText("Custom grid size");
    fireEvent.change(input, { target: { value: "1" } });
    expect(screen.getByText("4×4 = 16 pieces")).toBeInTheDocument();
  });

  it("Start button calls onStart('puzzle', gridSize)", () => {
    const onStart = vi.fn();
    render(<ModeSelect files={[makeImageFile()]} onStart={onStart} />);
    // Default gridSize is 4
    fireEvent.click(screen.getByText("Start"));
    expect(onStart).toHaveBeenCalledWith("puzzle", 4);
  });

  it("clicking number input stops propagation (onClick handler covered)", () => {
    render(
      <ModeSelect files={[makeImageFile()]} onStart={() => undefined} />,
    );
    const input = screen.getByLabelText("Custom grid size");
    fireEvent.click(input); // covers onClick={(e) => { e.stopPropagation(); }}
  });

  it("Start button uses updated grid size after preset click", () => {
    const onStart = vi.fn();
    render(<ModeSelect files={[makeImageFile()]} onStart={onStart} />);
    fireEvent.click(screen.getByText("5×5"));
    fireEvent.click(screen.getByText("Start"));
    expect(onStart).toHaveBeenCalledWith("puzzle", 5);
  });
});
