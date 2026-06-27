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
  const [phase, setPhase] = useState<GamePhase>("drop");
  const [files, setFiles] = useState<File[]>([]);
  const [mode, setMode] = useState<TransferMode>("download");
  const [puzzleGridSize, setPuzzleGridSize] = useState(4);
  const [fileResult, setFileResult] = useState<FileGameResult | null>(null);
  const [puzzleResult, setPuzzleResult] = useState<PuzzleGameResult | null>(null);

  const handleFiles = useCallback((incoming: File[]) => {
    setFiles(incoming);
    setPhase("mode");
  }, []);

  const handlePuzzleDirect = useCallback((imageFile: File, gridSize: number) => {
    setFiles([imageFile]);
    setMode("puzzle");
    setPuzzleGridSize(gridSize);
    setPhase("playing");
  }, []);

  const handleStart = useCallback((selected: TransferMode, gridSize = 4) => {
    setMode(selected);
    if (selected === "puzzle") setPuzzleGridSize(gridSize);
    setPhase("playing");
  }, []);

  const handleFileDone = useCallback((result: FileGameResult) => {
    setFileResult(result);
    setPhase("done");
  }, []);

  const handlePuzzleDone = useCallback((result: PuzzleGameResult) => {
    setPuzzleResult(result);
    setPhase("done");
  }, []);

  const handleRestart = useCallback(() => {
    setFiles([]);
    setFileResult(null);
    setPuzzleResult(null);
    setPhase("drop");
  }, []);

  if (phase === "drop") {
    return <DropZone onFiles={handleFiles} onPuzzle={handlePuzzleDirect} />;
  }
  if (phase === "mode") {
    return <ModeSelect files={files} onStart={handleStart} />;
  }
  if (phase === "playing") {
    if (mode === "puzzle") {
      return (
        <PuzzleCanvas
          imageFile={files[0]!}
          gridSize={puzzleGridSize}
          onDone={handlePuzzleDone}
        />
      );
    }
    return <GameCanvas files={files} onDone={handleFileDone} />;
  }
  // done phase — puzzleResult is non-null iff mode was "puzzle"
  if (puzzleResult !== null) {
    return <PuzzleResult result={puzzleResult} onRestart={handleRestart} />;
  }
  return (
    <ScoreScreen
      result={fileResult!}
      mode={mode}
      onRestart={handleRestart}
    />
  );
}
