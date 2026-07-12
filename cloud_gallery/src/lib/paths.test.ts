import { describe, it, expect } from "vitest";
import {
  basename,
  crumbs,
  encodePath,
  extname,
  humanSize,
  isImage,
  isText,
  isVideo,
  joinPath,
  normalize,
  parentPath,
} from "./paths.ts";

describe("extname", () => {
  it("returns lower-case extension without dot", () => {
    expect(extname("PIC.JPG")).toBe("jpg");
    expect(extname("a.tar.gz")).toBe("gz");
  });
  it("returns empty for no/edge extensions", () => {
    expect(extname("README")).toBe("");
    expect(extname(".hidden")).toBe("");
    expect(extname("trailing.")).toBe("");
  });
});

describe("type predicates", () => {
  it("classifies images, videos and text", () => {
    expect(isImage("a.png")).toBe(true);
    expect(isImage("a.mp4")).toBe(false);
    expect(isVideo("a.mkv")).toBe(true);
    expect(isVideo("a.png")).toBe(false);
    expect(isText("notes.md")).toBe(true);
    expect(isText("a.bin")).toBe(false);
  });
});

describe("normalize / join / parent / basename", () => {
  it("normalizes dots and slashes", () => {
    expect(normalize("/a//b/./c")).toBe("/a/b/c");
    expect(normalize("/a/b/../c")).toBe("/a/c");
    expect(normalize("")).toBe("/");
    expect(normalize("/")).toBe("/");
  });
  it("joins and finds parents / basenames", () => {
    expect(joinPath("/a/b", "c.jpg")).toBe("/a/b/c.jpg");
    expect(parentPath("/a/b/c.jpg")).toBe("/a/b");
    expect(parentPath("/")).toBe("/");
    expect(parentPath("/only")).toBe("/");
    expect(basename("/a/b/c.jpg")).toBe("c.jpg");
    expect(basename("/")).toBe("/");
  });
});

describe("encodePath", () => {
  it("encodes each segment", () => {
    expect(encodePath("/Media/2026/07/a b.jpg")).toBe("/Media/2026/07/a%20b.jpg");
    expect(encodePath("/")).toBe("/");
  });
});

describe("crumbs", () => {
  it("builds breadcrumb trail", () => {
    expect(crumbs("/")).toEqual([{ name: "cloud", path: "/" }]);
    expect(crumbs("/Media/2026")).toEqual([
      { name: "cloud", path: "/" },
      { name: "Media", path: "/Media" },
      { name: "2026", path: "/Media/2026" },
    ]);
  });
});

describe("humanSize", () => {
  it("formats bytes across units", () => {
    expect(humanSize(512)).toBe("512 B");
    expect(humanSize(1536)).toBe("1.5 KB");
    expect(humanSize(5 * 1024 * 1024)).toBe("5.0 MB");
    expect(humanSize(3 * 1024 * 1024 * 1024)).toBe("3.0 GB");
    expect(humanSize(2 * 1024 ** 4)).toBe("2.0 TB");
    expect(humanSize(50 * 1024)).toBe("50 KB");
  });
});
