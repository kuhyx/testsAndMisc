import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:file_picker/file_picker.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:xml/xml.dart';

/// Service that picks a file from the device and parses it into a [Script].
///
/// Supports `.txt`, `.docx`, and `.pdf` formats.
class FileImportService {
  /// Creates a [FileImportService].
  const FileImportService();

  /// Supported file extensions for import.
  static const supportedExtensions = ['txt', 'text', 'docx', 'pdf'];

  /// Opens a file picker and parses the selected file.
  ///
  /// Returns `null` if the user cancels.
  /// Throws [FormatException] if the file cannot be parsed.
  Future<Script?> pickAndParse() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: supportedExtensions,
      withData: true,
    );

    if (result == null || result.files.isEmpty) return null;

    final file = result.files.first;
    if (file.bytes == null) {
      throw const FormatException('Could not read file data.');
    }

    final title = file.name.replaceAll(RegExp(r'\.[^.]+$'), '');
    final content = await _extractText(file.bytes!, file.extension ?? '');
    final parser = TextParser();

    return parser.parse(content: content, title: title);
  }

  /// Parses a script from raw bytes and a file name.
  ///
  /// Used by drag-and-drop import where [FilePicker] is not involved.
  Future<Script?> parseBytes({
    required Uint8List bytes,
    required String fileName,
  }) async {
    final extension = fileName.split('.').last.toLowerCase();
    final title = fileName.replaceAll(RegExp(r'\.[^.]+$'), '');
    final content = await _extractText(bytes, extension);
    final parser = TextParser();

    return parser.parse(content: content, title: title);
  }

  Future<String> _extractText(Uint8List bytes, String extension) async {
    final ext = extension.toLowerCase();
    if (ext == 'docx') return _extractDocx(bytes);
    if (ext == 'pdf') return _extractPdf(bytes);
    return String.fromCharCodes(bytes);
  }

  /// Extracts text from a .docx file (ZIP archive containing XML).
  String _extractDocx(Uint8List bytes) {
    final archive = ZipDecoder().decodeBytes(bytes);
    final docFile = archive.findFile('word/document.xml');
    if (docFile == null) {
      throw const FormatException(
        'Invalid .docx file: missing word/document.xml',
      );
    }

    final xml = XmlDocument.parse(String.fromCharCodes(docFile.content as List<int>));
    final paragraphs = <String>[];

    for (final paragraph in xml.findAllElements('w:p')) {
      final texts = paragraph
          .findAllElements('w:t')
          .map((e) => e.innerText)
          .join();
      paragraphs.add(texts);
    }

    return paragraphs.join('\n');
  }

  /// Extracts text from a PDF using the system `pdftotext` utility.
  ///
  /// Requires `poppler` (provides `pdftotext`) to be installed.
  /// On Arch Linux: `pacman -S poppler`.
  Future<String> _extractPdf(Uint8List bytes) async {
    final tempDir = await Directory.systemTemp.createTemp('horatio_pdf_');
    final tempFile = File('${tempDir.path}/input.pdf');
    try {
      await tempFile.writeAsBytes(bytes);
      final result = await Process.run(
        'pdftotext',
        ['-layout', tempFile.path, '-'],
      );
      if (result.exitCode != 0) {
        throw FormatException(
          'PDF extraction failed. '
          'Ensure poppler is installed (pacman -S poppler).\n'
          '${result.stderr}',
        );
      }
      return (result.stdout as String).trim();
    } finally {
      await tempDir.delete(recursive: true);
    }
  }
}
