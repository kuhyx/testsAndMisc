import { useEffect, useRef } from "react";

const BASKET_HALF_WIDTH = 60;

/**
 * Tracks mouse X on the canvas and keeps a ref updated with the clamped basket
 * centre X. Uses a ref (not state) to avoid re-renders inside the game loop.
 */
export function useBasketControl(
  canvasRef: React.RefObject<HTMLCanvasElement | null>,
): React.RefObject<number> {
  const basketXRef = useRef<number>(window.innerWidth / 2);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onMouseMove = (e: MouseEvent): void => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      basketXRef.current = Math.max(
        BASKET_HALF_WIDTH,
        Math.min(canvas.width - BASKET_HALF_WIDTH, x),
      );
    };

    canvas.addEventListener("mousemove", onMouseMove);
    return () => { canvas.removeEventListener("mousemove", onMouseMove); };
  }, [canvasRef]);

  return basketXRef;
}
