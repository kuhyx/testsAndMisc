import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/services/file_import_service.dart';
import 'package:mocktail/mocktail.dart';
import 'package:plugin_platform_interface/plugin_platform_interface.dart';

class _MockFilePicker extends Mock
    with MockPlatformInterfaceMixin
    implements FilePicker {}

void main() {
  group('FileImportService', () {
    const service = FileImportService();

    test('supportedExtensions contains expected types', () {
      expect(
        FileImportService.supportedExtensions,
        containsAll(['txt', 'text', 'docx', 'pdf']),
      );
    });

    test('parseBytes parses plain text file', () async {
      const content = 'HAMLET: To be.\nHORATIO: Indeed.';
      final bytes = Uint8List.fromList(content.codeUnits);
      final script = await service.parseBytes(
        bytes: bytes,
        fileName: 'hamlet.txt',
      );
      expect(script, isNotNull);
      expect(script!.title, 'hamlet');
      expect(script.roles, hasLength(2));
    });

    test('parseBytes handles .text extension', () async {
      const content = 'A: Hello.\nB: World.';
      final bytes = Uint8List.fromList(content.codeUnits);
      final script = await service.parseBytes(
        bytes: bytes,
        fileName: 'test.text',
      );
      expect(script, isNotNull);
      expect(script!.title, 'test');
    });

    test('parseBytes throws FormatException for invalid .docx', () async {
      // Invalid ZIP data should fail to parse as docx.
      final bytes = Uint8List.fromList([1, 2, 3, 4]);
      expect(
        () => service.parseBytes(bytes: bytes, fileName: 'bad.docx'),
        throwsA(isA<Exception>()),
      );
    });

    test('parseBytes parses valid .docx file', () async {
      // Build a minimal .docx (ZIP containing word/document.xml).
      const xml = '<?xml version="1.0"?>'
          ' <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
          ' <w:body>'
          ' <w:p><w:r><w:t>ROMEO: Hello world.</w:t></w:r></w:p>'
          ' <w:p><w:r><w:t>JULIET: Hi there.</w:t></w:r></w:p>'
          ' </w:body></w:document>';

      final archive = Archive()
        ..addFile(ArchiveFile.bytes(
          'word/document.xml',
          Uint8List.fromList(xml.codeUnits),
        ));
      final zipBytes = Uint8List.fromList(ZipEncoder().encode(archive));

      final script = await service.parseBytes(
        bytes: zipBytes,
        fileName: 'play.docx',
      );
      expect(script, isNotNull);
      expect(script!.title, 'play');
      expect(script.roles, hasLength(2));
    });

    test('parseBytes docx missing word/document.xml throws', () async {
      // ZIP without the expected file.
      final archive = Archive()
        ..addFile(ArchiveFile.bytes(
          'other.xml',
          Uint8List.fromList('<x/>'.codeUnits),
        ));
      final zipBytes = Uint8List.fromList(ZipEncoder().encode(archive));

      expect(
        () => service.parseBytes(bytes: zipBytes, fileName: 'no_doc.docx'),
        throwsA(isA<FormatException>().having(
          (e) => e.message,
          'message',
          contains('missing word/document.xml'),
        )),
      );
    });

    test('parseBytes parses a valid PDF file via pdftotext', () async {
      // Minimal valid PDF with "HAMLET: Hello." text content.
      const pdfString = '%PDF-1.0\n'
          '1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
          '2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
          '3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]'
          ' /Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n'
          '4 0 obj\n<</Length 44>>\nstream\n'
          'BT /F1 12 Tf 100 700 Td (HAMLET: Hello.) Tj ET\n'
          'endstream\nendobj\n'
          '5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n'
          'xref\n0 6\n'
          '0000000000 65535 f \n'
          '0000000009 00000 n \n'
          '0000000058 00000 n \n'
          '0000000115 00000 n \n'
          '0000000266 00000 n \n'
          '0000000360 00000 n \n'
          'trailer<</Size 6/Root 1 0 R>>\n'
          'startxref\n441\n%%EOF';

      final bytes = Uint8List.fromList(pdfString.codeUnits);
      final script = await service.parseBytes(
        bytes: bytes,
        fileName: 'hamlet.pdf',
      );
      expect(script, isNotNull);
      expect(script!.title, 'hamlet');
    });

    test('parseBytes throws FormatException for corrupted PDF', () async {
      final bytes = Uint8List.fromList('not a real pdf'.codeUnits);
      expect(
        () => service.parseBytes(bytes: bytes, fileName: 'bad.pdf'),
        throwsA(isA<FormatException>()),
      );
    });

    group('pickAndParse', () {
      late _MockFilePicker mockPicker;

      setUpAll(() {
        registerFallbackValue(FileType.any);
      });

      setUp(() {
        mockPicker = _MockFilePicker();
        FilePicker.platform = mockPicker;
      });

      void stubPickFiles(FilePickerResult? result) {
        when(() => mockPicker.pickFiles(
              type: any(named: 'type'),
              allowedExtensions: any(named: 'allowedExtensions'),
              withData: any(named: 'withData'),
            )).thenAnswer((_) async => result);
      }

      test('returns null when user cancels', () async {
        stubPickFiles(null);

        final result = await service.pickAndParse();
        expect(result, isNull);
      });

      test('returns null when files list is empty', () async {
        stubPickFiles(const FilePickerResult([]));

        final result = await service.pickAndParse();
        expect(result, isNull);
      });

      test('throws when bytes are null', () async {
        stubPickFiles(FilePickerResult([
          PlatformFile(name: 'test.txt', size: 0),
        ]));

        expect(
          () => service.pickAndParse(),
          throwsA(isA<FormatException>().having(
            (e) => e.message,
            'message',
            contains('Could not read file data'),
          )),
        );
      });

      test('parses a picked txt file', () async {
        const content = 'HAMLET: To be.\nHORATIO: Indeed.';
        stubPickFiles(FilePickerResult([
          PlatformFile(
            name: 'play.txt',
            size: content.length,
            bytes: Uint8List.fromList(content.codeUnits),
          ),
        ]));

        final script = await service.pickAndParse();
        expect(script, isNotNull);
        expect(script!.title, 'play');
        expect(script.roles, hasLength(2));
      });
    });
  });
}
