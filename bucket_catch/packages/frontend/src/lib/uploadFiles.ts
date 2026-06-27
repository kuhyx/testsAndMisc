const BACKEND_URL = "http://localhost:3000/files/upload";

export interface UploadResult {
  filename: string;
  originalname: string;
  size: number;
  savedAt: string;
}

/** Upload a single file to the backend. */
async function uploadOne(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(BACKEND_URL, { method: "POST", body: form });
  if (!res.ok) {
    throw new Error(`Upload failed for ${file.name}: ${res.statusText}`);
  }
  return res.json() as Promise<UploadResult>;
}

/** Upload all caught files sequentially to the backend. */
export async function uploadFiles(files: File[]): Promise<UploadResult[]> {
  const results: UploadResult[] = [];
  for (const file of files) {
    results.push(await uploadOne(file));
  }
  return results;
}
