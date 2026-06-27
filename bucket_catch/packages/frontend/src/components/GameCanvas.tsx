import React, { useEffect, useRef } from "react";
import type { FileGameResult } from "../types";
import { useBasketControl } from "../hooks/useBasketControl";
import { useGameLoop } from "../hooks/useGameLoop";
import styles from "./GameCanvas.module.css";

interface Props {
  files: File[];
  onDone: (result: FileGameResult) => void;
}

export function GameCanvas({ files, onDone }: Props): React.ReactElement {
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

  const result = useGameLoop(canvasRef, basketXRef, files, true);

  useEffect(() => {
    if (result) onDone(result);
  }, [result, onDone]);

  return (
    <div className={styles.wrapper}>
      <canvas ref={canvasRef} className={styles.canvas} />
      <div className={styles.hint}>Move mouse to control the basket</div>
    </div>
  );
}
