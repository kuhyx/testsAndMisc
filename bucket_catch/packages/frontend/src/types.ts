export type GamePhase = "drop" | "mode" | "playing" | "done";

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

export type GameResult = FileGameResult | PuzzleGameResult;
