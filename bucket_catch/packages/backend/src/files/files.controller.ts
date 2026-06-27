import {
  Controller,
  Post,
  UploadedFile,
  UseInterceptors,
  BadRequestException,
} from "@nestjs/common";
import { FileInterceptor } from "@nestjs/platform-express";
import { diskStorage } from "multer";
import { extname } from "path";
import { FilesService, UploadResult } from "./files.service";

@Controller("files")
export class FilesController {
  constructor(private readonly filesService: FilesService) {}

  @Post("upload")
  @UseInterceptors(
    FileInterceptor("file", {
      storage: diskStorage({
        destination: "./uploads",
        filename: (_req, file, cb) => {
          const uniqueSuffix = `${Date.now().toString()}-${Math.round(Math.random() * 1e9).toString()}`;
          cb(null, uniqueSuffix + extname(file.originalname));
        },
      }),
      limits: { fileSize: 100 * 1024 * 1024 }, // 100 MB
    }),
  )
  uploadFile(
    @UploadedFile() file: Express.Multer.File | undefined,
  ): UploadResult {
    if (!file) {
      throw new BadRequestException("No file provided");
    }
    return this.filesService.processUpload(file);
  }
}
