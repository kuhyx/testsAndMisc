/** Inventory IO component tests. */

/** Result panel and inventory IO component tests. */

/** Badge picker and result panel component tests. */

/** Row, list and picker component tests. */

/**
 * Component tests for the three ways of entering an inventory: clicking a die,
 * scrolling the wheel over its counter, and fuzzy-searching by name.
 */

import { fireEvent, render, screen, waitFor, } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { SavedInventory } from "../lib/inventoryIo.ts";
import { InventoryIo } from "./InventoryIo.tsx";
import type { InventoryIoProps } from "./InventoryIo.tsx";

/**
 * Apply the updater a component emitted, to assert on the resulting count.
 *
 * @param mock - The mocked onChange.
 * @param previous - The count it should be applied to.
 * @param call - Which call to read, counting from the end by default.
 * @returns The count the component asked for.
 */


describe("InventoryIo", () => {
  const inventory: SavedInventory = {
    diceCounts: { weighted: 2 },
    badgeIds: ["tin_might"],
  };

  /**
   * Render the panel with every port stubbed, and open it.
   *
   * @param overrides - Ports or handlers to replace.
   * @returns The stubs the caller will want to assert on.
   */
  function setup(overrides: Partial<InventoryIoProps> = {}) {
    const onImport = vi.fn();
    const saveFile = vi.fn();
    const clipboard = { writeText: vi.fn<(text: string) => Promise<void>>().mockResolvedValue() };
    render(
      <InventoryIo
        inventory={inventory}
        onImport={onImport}
        clipboard={clipboard}
        saveFile={saveFile}
        shareUrl="https://dice.example/#i=abc"
        {...overrides}
      />,
    );
    return { onImport, saveFile, clipboard };
  }

  it("starts collapsed so it costs no vertical space", () => {
    setup();
    expect(screen.getByText("Import / export").closest("details")).not.toHaveAttribute("open");
  });

  it("downloads the inventory as parseable JSON", async () => {
    const { saveFile } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Download .json" }));
    expect(saveFile).toHaveBeenCalledTimes(1);
    const [filename, body] = saveFile.mock.calls[0] as [string, string];
    expect(filename).toBe("kcd2-dice.json");
    expect(JSON.parse(body)).toEqual(inventory);
    expect(screen.getByRole("status")).toHaveTextContent("Saved kcd2-dice.json.");
  });

  it("copies the JSON to the clipboard", async () => {
    const { clipboard } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Copy JSON" }));
    expect(JSON.parse(clipboard.writeText.mock.calls[0][0])).toEqual(inventory);
    await screen.findByText("JSON copied.");
  });

  it("copies the share link", async () => {
    const { clipboard } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Copy link" }));
    expect(clipboard.writeText).toHaveBeenCalledWith("https://dice.example/#i=abc");
    await screen.findByText("Link copied.");
  });

  it("falls back to the textarea when the clipboard refuses", async () => {
    // Insecure origins reject; the payload must still be reachable by hand.
    const clipboard = {
      writeText: vi.fn<(text: string) => Promise<void>>().mockRejectedValue(new Error("denied")),
    };
    setup({ clipboard });
    await userEvent.click(screen.getByRole("button", { name: "Copy JSON" }));
    await screen.findByText(/Copy failed/);
    const box = screen.getByLabelText<HTMLTextAreaElement>("Inventory JSON");
    expect(JSON.parse(box.value)).toEqual(inventory);
  });

  it("imports a pasted inventory", async () => {
    const { onImport } = setup();
    // fireEvent rather than userEvent.type: the latter treats "{" and "[" as
    // key-descriptor syntax, which mangles JSON.
    fireEvent.change(screen.getByLabelText("Inventory JSON"), {
      target: { value: JSON.stringify({ diceCounts: { lucky: 3 }, badgeIds: [] }) },
    });
    await userEvent.click(screen.getByRole("button", { name: "Import pasted" }));
    expect(onImport).toHaveBeenCalledWith({ diceCounts: { lucky: 3 }, badgeIds: [] });
    expect(screen.getByRole("status")).toHaveTextContent("Imported.");
  });

  it("refuses an unusable payload without calling onImport", async () => {
    const { onImport } = setup();
    fireEvent.change(screen.getByLabelText("Inventory JSON"), { target: { value: "{not json" } });
    await userEvent.click(screen.getByRole("button", { name: "Import pasted" }));
    expect(onImport).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent("Nothing imported. Not valid JSON.");
  });

  it("imports what it can and says what it ignored", async () => {
    const { onImport } = setup();
    fireEvent.change(screen.getByLabelText("Inventory JSON"), {
      target: { value: '{"diceCounts":{"lucky":1,"nope":2},"badgeIds":[]}' },
    });
    await userEvent.click(screen.getByRole("button", { name: "Import pasted" }));
    expect(onImport).toHaveBeenCalledWith({ diceCounts: { lucky: 1 }, badgeIds: [] });
    expect(screen.getByRole("status")).toHaveTextContent("Ignored: Unknown die “nope”.");
  });

  it("keeps the import button disabled until something is pasted", () => {
    setup();
    expect(screen.getByRole("button", { name: "Import pasted" })).toBeDisabled();
  });

  it("imports an uploaded file", async () => {
    const { onImport } = setup();
    const file = new File([JSON.stringify({ diceCounts: { lucky: 5 }, badgeIds: [] })], "inv.json", {
      type: "application/json",
    });
    await userEvent.upload(screen.getByLabelText(/Load a .json file/), file);
    await waitFor(() => {
      expect(onImport).toHaveBeenCalledWith({ diceCounts: { lucky: 5 }, badgeIds: [] });
    });
  });

  it("does nothing when the file picker is dismissed", () => {
    const { onImport } = setup();
    const input = screen.getByLabelText(/Load a .json file/);
    fireEvent.change(input, { target: { files: [] } });
    expect(onImport).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { files: null } });
    expect(onImport).not.toHaveBeenCalled();
  });

  it("reports a file it cannot read", async () => {
    const { onImport } = setup();
    const unreadable = new File(["x"], "bad.json", { type: "application/json" });
    vi.spyOn(unreadable, "text").mockRejectedValue(new Error("I/O"));
    await userEvent.upload(screen.getByLabelText(/Load a .json file/), unreadable);
    await screen.findByText("Could not read that file.");
    expect(onImport).not.toHaveBeenCalled();
  });
});
