/**
 * Moving an inventory between devices: a file, the clipboard, or a link.
 *
 * Collapsed by default and placed below the badges, because the dice grid above
 * it spends the whole of a phone screen and a summary line up there would cost
 * a row of dice.
 */

import { useState } from "react";
import type { ChangeEvent, JSX } from "react";
import {
  EXPORT_FILENAME,
  isUsable,
  parseInventoryJson,
  serialiseInventory,
} from "../lib/inventoryIo.ts";
import type { ClipboardPort, SavedInventory, SaveFilePort } from "../lib/inventoryIo.ts";

export interface InventoryIoProps {
  readonly inventory: SavedInventory;
  readonly onImport: (inventory: SavedInventory) => void;
  readonly clipboard: ClipboardPort;
  readonly saveFile: SaveFilePort;
  /** Absolute URL carrying this inventory in its fragment. */
  readonly shareUrl: string;
}

interface Status {
  readonly ok: boolean;
  readonly message: string;
}

/**
 * Import and export controls for the saved inventory.
 *
 * @param props - The current inventory, an import handler, and the injectable
 *   clipboard and download ports.
 * @returns The collapsible panel.
 */
export function InventoryIo({
  inventory,
  onImport,
  clipboard,
  saveFile,
  shareUrl,
}: InventoryIoProps): JSX.Element {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<Status | null>(null);

  const json = serialiseInventory(inventory);

  const apply = (raw: string): void => {
    const result = parseInventoryJson(raw);
    const { inventory: parsed, dropped } = result;
    if (!isUsable(result)) {
      setStatus({ ok: false, message: `Nothing imported. ${dropped.join(" ")}` });
      return;
    }
    onImport(parsed);
    setStatus({
      ok: true,
      message: dropped.length === 0 ? "Imported." : `Imported. Ignored: ${dropped.join(" ")}`,
    });
  };

  const copy = (value: string, what: string): void => {
    void clipboard.writeText(value).then(
      () => {
        setStatus({ ok: true, message: `${what} copied.` });
      },
      () => {
        // Insecure origin, or a browser that refuses without a user gesture.
        // Put the payload in the box so it can still be copied by hand.
        setText(value);
        setStatus({ ok: false, message: "Copy failed — select the text below and copy it." });
      },
    );
  };

  const onFile = (event: ChangeEvent<HTMLInputElement>): void => {
    const { files } = event.target;
    if (files === null || files.length === 0) {
      return;
    }
    void files[0].text().then(apply, () => {
      setStatus({ ok: false, message: "Could not read that file." });
    });
  };

  return (
    <details className="io">
      <summary>Import / export</summary>

      <div className="io-row">
        <button
          type="button"
          className="clear"
          onClick={() => {
            saveFile(EXPORT_FILENAME, json);
            setStatus({ ok: true, message: `Saved ${EXPORT_FILENAME}.` });
          }}
        >
          Download .json
        </button>
        <button
          type="button"
          className="clear"
          onClick={() => {
            copy(json, "JSON");
          }}
        >
          Copy JSON
        </button>
        <button
          type="button"
          className="clear"
          onClick={() => {
            copy(shareUrl, "Link");
          }}
        >
          Copy link
        </button>
      </div>

      <label className="io-file">
        Load a .json file
        <input type="file" accept="application/json" onChange={onFile} />
      </label>

      <textarea
        className="io-text"
        rows={4}
        placeholder="…or paste an exported inventory here"
        aria-label="Inventory JSON"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
        }}
      />

      <div className="io-row">
        <button
          type="button"
          className="clear"
          disabled={text.trim() === ""}
          onClick={() => {
            apply(text);
          }}
        >
          Import pasted
        </button>
      </div>

      {status !== null && (
        <p className={status.ok ? "io-status" : "io-status bad"} role="status">
          {status.message}
        </p>
      )}
    </details>
  );
}
