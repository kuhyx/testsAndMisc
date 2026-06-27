/** Returns an emoji representing the file type based on MIME or extension. */
export function fileIcon(file: File): string {
  const mime = file.type;
  if (mime.startsWith("image/")) return "🖼️";
  if (mime.startsWith("video/")) return "🎬";
  if (mime.startsWith("audio/")) return "🎵";
  if (mime === "application/pdf") return "📄";
  if (
    mime === "application/zip" ||
    mime === "application/x-zip-compressed" ||
    file.name.endsWith(".zip") ||
    file.name.endsWith(".tar.gz") ||
    file.name.endsWith(".rar")
  )
    return "📦";
  if (
    mime.includes("javascript") ||
    mime.includes("typescript") ||
    (/\.(ts|tsx|js|jsx|py|go|rs|c|cpp|java|sh)$/.exec(file.name))
  )
    return "💻";
  if (
    mime.includes("text") ||
    (/\.(txt|md|csv|log)$/.exec(file.name))
  )
    return "📝";
  return "📎";
}

/** Truncate a filename to at most `max` characters, keeping extension. */
export function truncateFilename(name: string, max = 18): string {
  if (name.length <= max) return name;
  const dot = name.lastIndexOf(".");
  if (dot > 0) {
    const ext = name.slice(dot);
    return name.slice(0, max - ext.length - 1) + "…" + ext;
  }
  return name.slice(0, max - 1) + "…";
}

/** Human-readable file size. */
export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
