/**
 * Where the app is. The done phase carries its result, so "finished with no
 * result" cannot be represented and the render never has to assert one away.
 */
export type GamePhase =
  | { kind: "drop" }
  | { kind: "mode" }
  | { kind: "playing" }
  | { kind: "done"; result: GameResult };

export type TransferMode = "download" | "upload" | "puzzle";

export interface FallingFileItem {
  readonly kind: "file";
  readonly id: string;
  readonly file: File;
  x: number;
  y: number;
  readonly speed: number;
  readonly startFrame: number;
  status: "falling" | "caught" | "missed";
}

export interface PuzzlePiece {
  readonly row: number;
  readonly col: number;
  readonly gridSize: number;
  readonly imageUrl: string;
  readonly pieceWidth: number;
  readonly pieceHeight: number;
}

export interface FallingPuzzleItem {
  readonly kind: "puzzle";
  readonly id: string;
  readonly piece: PuzzlePiece;
  x: number;
  y: number;
  readonly speed: number;
  readonly startFrame: number;
  status: "falling" | "caught" | "missed";
}

export type FallingItem = FallingFileItem | FallingPuzzleItem;

export interface BasketState {
  x: number;
  width: number;
  height: number;
}

export interface FileGameResult {
  caught: File[];
  missed: File[];
}

export interface PuzzleGameResult {
  caughtPieces: FallingPuzzleItem[];
  missedPieces: FallingPuzzleItem[];
  gridSize: number;
}

/** The outcome of a finished game, tagged by which mode produced it. */
export type GameResult =
  | { kind: "file"; value: FileGameResult }
  | { kind: "puzzle"; value: PuzzleGameResult };
