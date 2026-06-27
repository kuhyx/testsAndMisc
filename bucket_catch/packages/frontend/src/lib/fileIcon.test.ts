import { describe, it, expect } from "vitest";
import { fileIcon, truncateFilename, formatSize } from "./fileIcon";

const makeFile = (name: string, type = "") =>
  new File([""], name, { type });

describe("fileIcon", () => {
  it("returns image emoji for image/* MIME", () => {
    expect(fileIcon(makeFile("a.png", "image/png"))).toBe("🖼️");
  });
  it("returns video emoji for video/* MIME", () => {
    expect(fileIcon(makeFile("a.mp4", "video/mp4"))).toBe("🎬");
  });
  it("returns audio emoji for audio/* MIME", () => {
    expect(fileIcon(makeFile("a.mp3", "audio/mpeg"))).toBe("🎵");
  });
  it("returns pdf emoji for application/pdf", () => {
    expect(fileIcon(makeFile("a.pdf", "application/pdf"))).toBe("📄");
  });
  it("returns archive emoji for application/zip", () => {
    expect(fileIcon(makeFile("a.zip", "application/zip"))).toBe("📦");
  });
  it("returns archive emoji for application/x-zip-compressed", () => {
    expect(fileIcon(makeFile("a.zip", "application/x-zip-compressed"))).toBe("📦");
  });
  it("returns archive emoji for .zip extension", () => {
    expect(fileIcon(makeFile("a.zip"))).toBe("📦");
  });
  it("returns archive emoji for .tar.gz extension", () => {
    expect(fileIcon(makeFile("a.tar.gz"))).toBe("📦");
  });
  it("returns archive emoji for .rar extension", () => {
    expect(fileIcon(makeFile("a.rar"))).toBe("📦");
  });
  it("returns code emoji for javascript MIME", () => {
    expect(fileIcon(makeFile("a.js", "application/javascript"))).toBe("💻");
  });
  it("returns code emoji for typescript MIME", () => {
    expect(fileIcon(makeFile("a.ts", "application/typescript"))).toBe("💻");
  });
  it("returns code emoji for .ts extension", () => {
    expect(fileIcon(makeFile("a.ts"))).toBe("💻");
  });
  it("returns code emoji for .tsx extension", () => {
    expect(fileIcon(makeFile("a.tsx"))).toBe("💻");
  });
  it("returns code emoji for .py extension", () => {
    expect(fileIcon(makeFile("a.py"))).toBe("💻");
  });
  it("returns code emoji for .go extension", () => {
    expect(fileIcon(makeFile("a.go"))).toBe("💻");
  });
  it("returns code emoji for .rs extension", () => {
    expect(fileIcon(makeFile("a.rs"))).toBe("💻");
  });
  it("returns code emoji for .c extension", () => {
    expect(fileIcon(makeFile("a.c"))).toBe("💻");
  });
  it("returns code emoji for .cpp extension", () => {
    expect(fileIcon(makeFile("a.cpp"))).toBe("💻");
  });
  it("returns code emoji for .java extension", () => {
    expect(fileIcon(makeFile("a.java"))).toBe("💻");
  });
  it("returns code emoji for .sh extension", () => {
    expect(fileIcon(makeFile("a.sh"))).toBe("💻");
  });
  it("returns text emoji for text/* MIME", () => {
    expect(fileIcon(makeFile("a.txt", "text/plain"))).toBe("📝");
  });
  it("returns text emoji for .md extension", () => {
    expect(fileIcon(makeFile("a.md"))).toBe("📝");
  });
  it("returns text emoji for .csv extension", () => {
    expect(fileIcon(makeFile("a.csv"))).toBe("📝");
  });
  it("returns text emoji for .log extension", () => {
    expect(fileIcon(makeFile("a.log"))).toBe("📝");
  });
  it("returns generic emoji for unknown type", () => {
    expect(fileIcon(makeFile("a.xyz"))).toBe("📎");
  });
});

describe("truncateFilename", () => {
  it("returns name unchanged when short enough", () => {
    expect(truncateFilename("hello.txt", 18)).toBe("hello.txt");
  });
  it("uses default max of 18", () => {
    expect(truncateFilename("short")).toBe("short");
  });
  it("truncates long name with extension", () => {
    const result = truncateFilename("averylongfilename.txt", 18);
    expect(result.length).toBeLessThanOrEqual(18);
    expect(result).toContain("…");
    expect(result).toContain(".txt");
  });
  it("truncates long name without extension", () => {
    const result = truncateFilename("averylongnamenoext", 10);
    expect(result.length).toBeLessThanOrEqual(10);
    expect(result).toContain("…");
  });
});

describe("formatSize", () => {
  it("formats bytes under 1 KB", () => {
    expect(formatSize(512)).toBe("512 B");
  });
  it("formats bytes under 1 MB as KB", () => {
    expect(formatSize(2048)).toBe("2.0 KB");
  });
  it("formats bytes 1 MB and over as MB", () => {
    expect(formatSize(2 * 1024 * 1024)).toBe("2.0 MB");
  });
});
