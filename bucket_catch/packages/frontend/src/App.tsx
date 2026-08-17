import React, { useCallback, useState } from "react";
import type {
  GamePhase,
  FileGameResult,
  PuzzleGameResult,
  TransferMode,
} from "./types";
import { DropZone } from "./components/DropZone";
import { ModeSelect } from "./components/ModeSelect";
import { GameCanvas } from "./components/GameCanvas";
import { PuzzleCanvas } from "./components/PuzzleCanvas";
import { ScoreScreen } from "./components/ScoreScreen";
import { PuzzleResult } from "./components/PuzzleResult";

export default function App(): React.ReactElement {
  const [phase, setPhase] = useState<GamePhase>({ kind: "drop" });
  const [files, setFiles] = useState<File[]>([]);
  const [mode, setMode] = useState<TransferMode>("download");
  const [puzzleGridSize, setPuzzleGridSize] = useState(4);

  const handleFiles = useCallback((incoming: File[]) => {
    setFiles(incoming);
    setPhase({ kind: "mode" });
  }, []);

  const handlePuzzleDirect = useCallback(
    (imageFile: File, gridSize: number) => {
      setFiles([imageFile]);
      setMode("puzzle");
      setPuzzleGridSize(gridSize);
      setPhase({ kind: "playing" });
    },
    [],
  );

  const handleStart = useCallback((selected: TransferMode, gridSize = 4) => {
    setMode(selected);
    if (selected === "puzzle") setPuzzleGridSize(gridSize);
    setPhase({ kind: "playing" });
  }, []);

  const handleFileDone = useCallback((value: FileGameResult) => {
    setPhase({ kind: "done", result: { kind: "file", value } });
  }, []);

  const handlePuzzleDone = useCallback((value: PuzzleGameResult) => {
    setPhase({ kind: "done", result: { kind: "puzzle", value } });
  }, []);

  const handleRestart = useCallback(() => {
    setFiles([]);
    setPhase({ kind: "drop" });
  }, []);

  if (phase.kind === "drop") {
    return <DropZone onFiles={handleFiles} onPuzzle={handlePuzzleDirect} />;
  }
  if (phase.kind === "mode") {
    return <ModeSelect files={files} onStart={handleStart} />;
  }
  if (phase.kind === "playing") {
    if (mode === "puzzle") {
      return (
        <PuzzleCanvas
          imageFile={files[0]}
          gridSize={puzzleGridSize}
          onDone={handlePuzzleDone}
        />
      );
    }
    return <GameCanvas files={files} onDone={handleFileDone} />;
  }
  // done phase: the phase carries its result, so both arms are non-null.
  if (phase.result.kind === "puzzle") {
    return (
      <PuzzleResult result={phase.result.value} onRestart={handleRestart} />
    );
  }
  return (
    <ScoreScreen
      result={phase.result.value}
      mode={mode}
      onRestart={handleRestart}
    />
  );
}
