import React, { useCallback, useState } from "react";
import type { TransferMode } from "../types";
import styles from "./ModeSelect.module.css";

const PRESETS = [2, 3, 4, 5, 6] as const;

interface Props {
  files: File[];
  onStart: (mode: TransferMode, gridSize?: number) => void;
}

export function ModeSelect({ files, onStart }: Props): React.ReactElement {
  const [gridSize, setGridSize] = useState(4);
  const fileCount = files.length;
  const isSingleImage =
    files.length === 1 && files[0].type.startsWith("image/");

  const handleGridChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = parseInt(e.target.value, 10);
      if (!isNaN(raw) && raw >= 2) setGridSize(raw);
    },
    [],
  );

  return (
    <div className={styles.container}>
      <h2 className={styles.heading}>
        {fileCount} file{fileCount !== 1 ? "s" : ""} ready to drop
      </h2>
      <p className={styles.sub}>What happens to the files you catch?</p>
      <div className={styles.cards}>
        <button
          className={styles.card}
          onClick={() => { onStart("download"); }}
        >
          <span className={styles.cardIcon}>⬇️</span>
          <span className={styles.cardTitle}>Download</span>
          <span className={styles.cardDesc}>
            Caught files are zipped and saved to your device. No server needed.
          </span>
        </button>
        <button
          className={styles.card}
          onClick={() => { onStart("upload"); }}
        >
          <span className={styles.cardIcon}>☁️</span>
          <span className={styles.cardTitle}>Upload</span>
          <span className={styles.cardDesc}>
            Caught files are sent to the backend server (localhost:3000).
          </span>
        </button>
        <div
          className={`${styles.card} ${isSingleImage ? styles.puzzleCard : styles.cardDisabled}`}
          title={isSingleImage ? "" : "Drop exactly one image file to unlock puzzle mode"}
        >
          <span className={styles.cardIcon}>🧩</span>
          <span className={styles.cardTitle}>Puzzle</span>
          <span className={styles.cardDesc}>
            {isSingleImage
              ? "Catch puzzle pieces to assemble your image!"
              : "Drop exactly one image file to play puzzle mode."}
          </span>
          {isSingleImage && (
            <>
              <div className={styles.gridRow}>
                {PRESETS.map((n) => (
                  <button
                    key={n}
                    className={`${styles.preset} ${gridSize === n ? styles.presetActive : ""}`}
                    onClick={(e) => { e.stopPropagation(); setGridSize(n); }}
                  >
                    {n}×{n}
                  </button>
                ))}
                <input
                  type="number"
                  min={2}
                  max={99}
                  value={gridSize}
                  onChange={handleGridChange}
                  onClick={(e) => { e.stopPropagation(); }}
                  className={styles.gridInput}
                  aria-label="Custom grid size"
                />
              </div>
              <p className={styles.gridEq}>{gridSize}×{gridSize} = {gridSize * gridSize} pieces</p>
              <button
                className={styles.puzzleStart}
                onClick={() => { onStart("puzzle", gridSize); }}
              >
                Start
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
