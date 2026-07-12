export type EntryKind = "dir" | "file";

/** One entry in a directory listing, as returned by the dufs WebDAV PROPFIND. */
export interface DirEntry {
  /** Base name, e.g. "pic.jpg". */
  readonly name: string;
  /** Absolute path from the cloud root, e.g. "/Media/2026/07/pic.jpg". */
  readonly path: string;
  readonly kind: EntryKind;
  /** Size in bytes (0 for directories). */
  readonly size: number;
  /** Last-modified time in epoch milliseconds (0 if unknown). */
  readonly mtimeMs: number;
}
