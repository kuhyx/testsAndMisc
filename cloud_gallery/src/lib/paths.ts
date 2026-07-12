/** Path and file-type helpers for cloud paths (absolute, from the cloud root). */

const IMAGE_EXTS = new Set([
  "jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp",
  "heic", "heif", "avif", "svg",
]);
const VIDEO_EXTS = new Set([
  "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v",
  "3gp", "ogv", "mpg", "mpeg", "mts", "m2ts", "vob",
]);
const TEXT_EXTS = new Set([
  "txt", "md", "markdown", "log", "csv", "json", "yaml", "yml",
  "ini", "conf", "sh", "toml", "xml",
]);

/** Lower-case extension without the dot, or "" if none. */
export function extname(name: string): string {
  const dot = name.lastIndexOf(".");
  if (dot <= 0 || dot === name.length - 1) return "";
  return name.slice(dot + 1).toLowerCase();
}

export function isImage(name: string): boolean {
  return IMAGE_EXTS.has(extname(name));
}
export function isVideo(name: string): boolean {
  return VIDEO_EXTS.has(extname(name));
}
export function isText(name: string): boolean {
  return TEXT_EXTS.has(extname(name));
}

/** Normalize to a leading-slash, no-trailing-slash absolute path ("/" stays "/"). */
export function normalize(path: string): string {
  const parts = path.split("/").filter((p) => p.length > 0 && p !== ".");
  const out: string[] = [];
  for (const p of parts) {
    if (p === "..") out.pop();
    else out.push(p);
  }
  return "/" + out.join("/");
}

export function joinPath(base: string, name: string): string {
  return normalize(`${base}/${name}`);
}

export function parentPath(path: string): string {
  const n = normalize(path);
  if (n === "/") return "/";
  return normalize(n.slice(0, n.lastIndexOf("/")) || "/");
}

export function basename(path: string): string {
  const n = normalize(path);
  if (n === "/") return "/";
  return n.slice(n.lastIndexOf("/") + 1);
}

/** Encode an absolute path into a same-origin URL, encoding each segment. */
export function encodePath(path: string): string {
  return (
    "/" +
    normalize(path)
      .split("/")
      .filter((p) => p.length > 0)
      .map((p) => encodeURIComponent(p))
      .join("/")
  );
}

/** Breadcrumb segments for a path: [{name, path}], root first. */
export function crumbs(path: string): readonly { name: string; path: string }[] {
  const n = normalize(path);
  const out: { name: string; path: string }[] = [{ name: "cloud", path: "/" }];
  if (n === "/") return out;
  let acc = "";
  for (const seg of n.split("/").filter((p) => p.length > 0)) {
    acc += "/" + seg;
    out.push({ name: seg, path: acc });
  }
  return out;
}

/** Human-readable byte size. */
export function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  let v = bytes / 1024;
  let unit = "KB";
  for (const next of ["MB", "GB", "TB"]) {
    if (v < 1024) break;
    v /= 1024;
    unit = next;
  }
  return `${v.toFixed(v < 10 ? 1 : 0)} ${unit}`;
}
