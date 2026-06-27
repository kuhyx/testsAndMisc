import { Injectable } from "@nestjs/common";

export interface UploadResult {
  filename: string;
  originalname: string;
  size: number;
  savedAt: string;
}

@Injectable()
export class FilesService {
  processUpload(file: Express.Multer.File): UploadResult {
    return {
      filename: file.filename,
      originalname: file.originalname,
      size: file.size,
      savedAt: new Date().toISOString(),
    };
  }
}
