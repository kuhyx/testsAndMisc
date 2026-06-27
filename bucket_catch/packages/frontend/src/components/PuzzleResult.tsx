import React from "react";
import type { PuzzleGameResult } from "../types";
import styles from "./PuzzleResult.module.css";

interface Props {
  result: PuzzleGameResult;
  onRestart: () => void;
}

function calcGrade(pct: number): string {
  if (pct >= 90) return "S";
  if (pct >= 75) return "A";
  if (pct >= 50) return "B";
  if (pct >= 25) return "C";
  return "D";
}

export function PuzzleResult({ result, onRestart }: Props): React.ReactElement {
  const total = result.gridSize * result.gridSize;
  const caught = result.caughtPieces.length;
  const pct = total === 0 ? 0 : Math.round((caught / total) * 100);
  const grade = calcGrade(pct);

  const cells = Array.from({ length: total }, (_, index) => {
    const row = Math.floor(index / result.gridSize);
    const col = index % result.gridSize;
    const piece = result.caughtPieces.find(
      (p) => p.piece.row === row && p.piece.col === col,
    );
    return { row, col, piece };
  });

  return (
    <div className={styles.container}>
      <div className={styles.scoreBox}>
        <div className={styles.grade}>{grade}</div>
        <div className={styles.pct}>{pct}%</div>
        <div className={styles.stats}>
          <span className={styles.caught}>
            ✅ {caught} / {total} pieces caught
          </span>
        </div>
      </div>

      <div
        className={styles.grid}
        style={{ gridTemplateColumns: `repeat(${result.gridSize}, 1fr)` }}
      >
        {cells.map(({ row, col, piece }) =>
          piece ? (
            <img
              key={`${row}-${col}`}
              src={piece.piece.imageUrl}
              className={styles.piece}
              alt={`Piece ${row}-${col}`}
            />
          ) : (
            <div key={`${row}-${col}`} className={styles.hole} />
          ),
        )}
      </div>

      <button className={styles.restartBtn} onClick={onRestart}>
        Play again
      </button>
    </div>
  );
}
