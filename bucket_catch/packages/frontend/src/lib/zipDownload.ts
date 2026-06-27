import JSZip from "jszip";

/** Bundle the given files into a zip and trigger a browser download. */
export async function zipDownload(files: File[]): Promise<void> {
  const zip = new JSZip();
  for (const file of files) {
    zip.file(file.name, file);
  }
  const blob = await zip.generateAsync({ type: "blob" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "caught-files.zip";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
