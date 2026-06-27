import React, { useCallback, useRef, useState } from "react";
import styles from "./DropZone.module.css";

const PRESETS = [2, 3, 4, 5, 6] as const;

interface Props {
  onFiles: (files: File[]) => void;
  onPuzzle: (imageFile: File, gridSize: number) => void;
}

export function DropZone({ onFiles, onPuzzle }: Props): React.ReactElement {
  const [dragging, setDragging] = useState(false);
  const [count, setCount] = useState(0);
  const [gridSize, setGridSize] = useState(4);
  const puzzleInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length === 0) return;
      setCount(files.length);
      onFiles(files);
    },
    [onFiles],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []);
      if (files.length === 0) return;
      setCount(files.length);
      onFiles(files);
    },
    [onFiles],
  );

  const handlePuzzleInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      onPuzzle(file, gridSize);
    },
    [onPuzzle, gridSize],
  );

  const handleGridChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = parseInt(e.target.value, 10);
      if (!isNaN(raw) && raw >= 2) setGridSize(raw);
    },
    [],
  );

  return (
    <div
      className={`${styles.zone} ${dragging ? styles.dragging : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => { setDragging(false); }}
      onDrop={handleDrop}
    >
      <div className={styles.inner}>
        <span className={styles.icon}>🪣</span>
        <h1 className={styles.title}>Bucket Catch</h1>
        <p className={styles.subtitle}>
          Drop your files here — then catch them before they fall!
        </p>
        {count > 0 && (
          <p className={styles.count}>
            {count} file{count !== 1 ? "s" : ""} ready
          </p>
        )}
        <label className={styles.browseBtn}>
          Or browse folder
          <input
            type="file"
            ref={(el) => el?.setAttribute("webkitdirectory", "")}
            multiple
            hidden
            onChange={handleFileInput}
          />
        </label>

        <div className={styles.divider}>or</div>

        <div className={styles.puzzleSection}>
          <div className={styles.gridRow}>
            <span className={styles.gridLabel}>Grid:</span>
            {PRESETS.map((n) => (
              <button
                key={n}
                className={`${styles.preset} ${gridSize === n ? styles.presetActive : ""}`}
                onClick={() => { setGridSize(n); }}
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
              className={styles.gridInput}
              aria-label="Custom grid size"
            />
          </div>
          <p className={styles.gridEq}>{gridSize}×{gridSize} = {gridSize * gridSize} pieces</p>
          <button
            className={styles.puzzleBtn}
            onClick={() => puzzleInputRef.current?.click()}
          >
            🧩 Play Puzzle Mode
          </button>
          <input
            ref={puzzleInputRef}
            type="file"
            accept="image/*"
            hidden
            onChange={handlePuzzleInput}
          />
        </div>
      </div>
    </div>
  );
}
