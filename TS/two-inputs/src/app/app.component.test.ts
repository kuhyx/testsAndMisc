import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@angular/core", () => ({
  Component: () => (target: unknown) => target,
}));
vi.mock("@angular/common", () => ({ CommonModule: {} }));
vi.mock("@angular/router", () => ({ RouterOutlet: {} }));
vi.mock("@angular/material/input", () => ({ MatInputModule: {} }));
vi.mock("@angular/material/button", () => ({ MatButtonModule: {} }));
vi.mock("@angular/forms", () => ({ FormsModule: {} }));

vi.mock("./pair-logic", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./pair-logic")>();
  return {
    ...actual,
    findCorrespondingValue: vi.fn(actual.findCorrespondingValue),
    findValidPairs: vi.fn(actual.findValidPairs),
    changeIndex: vi.fn(actual.changeIndex),
  };
});

import { AppComponent } from "./app.component";
import { findCorrespondingValue } from "./pair-logic";

describe("AppComponent", () => {
  let comp: AppComponent;

  beforeEach(() => {
    vi.mocked(findCorrespondingValue).mockRestore();
    comp = new AppComponent();
  });

  it("constructor initializes possibleValues with 6 symmetric pairs", () => {
    expect(comp.possibleValues).toEqual([
      [100, 225],
      [125, 200],
      [150, 175],
      [175, 150],
      [200, 125],
      [225, 100],
    ]);
  });

  it("ngOnInit recalculates possibleValues", () => {
    comp.step = 50;
    comp.min = 150;
    comp.max = 150;
    comp.targetValue = 300;
    comp.ngOnInit();
    expect(comp.possibleValues).toEqual([[150, 150]]);
  });

  it("updateInput recalculates possibleValues", () => {
    comp.step = 50;
    comp.min = 150;
    comp.max = 150;
    comp.targetValue = 300;
    comp.updateInput();
    expect(comp.possibleValues).toEqual([[150, 150]]);
  });

  it("upOne increments indexOne and updates pair", () => {
    comp.upOne();
    expect(comp.indexOne).toBe(1);
    expect(comp.inputOne).toBe(125);
    expect(comp.inputTwo).toBe(200);
  });

  it("downOne wraps to last index and updates pair", () => {
    comp.downOne();
    expect(comp.indexOne).toBe(5);
    expect(comp.inputOne).toBe(225);
    expect(comp.inputTwo).toBe(100);
  });

  it("upTwo increments indexTwo and updates pair", () => {
    comp.upTwo();
    expect(comp.indexTwo).toBe(1);
    expect(comp.inputTwo).toBe(200);
    expect(comp.inputOne).toBe(125);
  });

  it("downTwo wraps to last index and updates pair", () => {
    comp.downTwo();
    expect(comp.indexTwo).toBe(5);
    expect(comp.inputTwo).toBe(100);
    expect(comp.inputOne).toBe(225);
  });

  it("upOne wraps around at end", () => {
    comp.indexOne = 5;
    comp.upOne();
    expect(comp.indexOne).toBe(0);
  });

  it("downOne wraps around at start", () => {
    comp.indexOne = 0;
    comp.downOne();
    expect(comp.indexOne).toBe(5);
  });

  it("updateTwoValue does nothing when possibleValues is null", () => {
    comp.possibleValues = null;
    comp.updateTwoValue();
    expect(comp.inputOne).toBeNull();
    expect(comp.inputTwo).toBeNull();
  });

  it("updateTwoValue logs error when inputOne is undefined", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    comp.possibleValues = [[undefined as unknown as number, 225]];
    comp.indexOne = 0;
    comp.updateTwoValue();
    expect(spy).toHaveBeenCalledWith(
      "this.inputOne is null or undefined!: ",
      undefined,
      expect.anything(),
      0,
    );
    spy.mockRestore();
  });

  it("updateTwoValue logs error when findCorrespondingValue returns null", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.mocked(findCorrespondingValue).mockReturnValueOnce(null);
    comp.possibleValues = [[100, 225]];
    comp.indexOne = 0;
    comp.updateTwoValue();
    expect(spy).toHaveBeenCalledWith("result is null!");
    spy.mockRestore();
  });

  it("updateInput sets possibleValues to null when step is null", () => {
    comp.step = null;
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    comp.updateInput();
    expect(comp.possibleValues).toBeNull();
    spy.mockRestore();
  });

  it("upTwo skips update when possibleValues becomes null", () => {
    comp.step = null;
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    comp.upTwo();
    expect(comp.possibleValues).toBeNull();
    spy.mockRestore();
  });

  it("upTwo handles findCorrespondingValue returning null", () => {
    vi.mocked(findCorrespondingValue).mockReturnValueOnce(null);
    const originalInputOne = comp.inputOne;
    comp.upTwo();
    expect(comp.inputOne).toBe(originalInputOne);
  });

  it("downTwo skips update when possibleValues becomes null", () => {
    comp.step = null;
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    comp.downTwo();
    expect(comp.possibleValues).toBeNull();
    spy.mockRestore();
  });

  it("downTwo handles findCorrespondingValue returning null", () => {
    vi.mocked(findCorrespondingValue).mockReturnValueOnce(null);
    const originalInputOne = comp.inputOne;
    comp.downTwo();
    expect(comp.inputOne).toBe(originalInputOne);
  });
});
