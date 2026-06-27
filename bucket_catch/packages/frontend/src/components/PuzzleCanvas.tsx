import React, { useEffect, useRef } from "react";
import type { PuzzleGameResult } from "../types";
import { useBasketControl } from "../hooks/useBasketControl";
import { usePuzzleGameLoop } from "../hooks/usePuzzleGameLoop";
import styles from "./PuzzleCanvas.module.css";

interface Props {
  imageFile: File;
  gridSize: number;
  onDone: (result: PuzzleGameResult) => void;
}

export function PuzzleCanvas({
  imageFile,
  gridSize,
  onDone,
}: Props): React.ReactElement {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const basketXRef = useBasketControl(canvasRef);

  useEffect(() => {
    const resize = (): void => {
      const canvas = canvasRef.current;
      /* istanbul ignore next */
      if (!canvas) return;
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
    };
    resize();
    window.addEventListener("resize", resize);
    return () => { window.removeEventListener("resize", resize); };
  }, []);

  const result = usePuzzleGameLoop(canvasRef, basketXRef, imageFile, gridSize, true);

  useEffect(() => {
    if (result) onDone(result);
  }, [result, onDone]);

  return (
    <div className={styles.wrapper}>
      <canvas ref={canvasRef} className={styles.canvas} />
      <div className={styles.hint}>Move mouse to catch the puzzle pieces!</div>
    </div>
  );
}
