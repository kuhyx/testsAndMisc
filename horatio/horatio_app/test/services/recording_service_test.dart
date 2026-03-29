import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:mocktail/mocktail.dart';
import 'package:record/record.dart';

class MockAudioRecorder extends Mock implements AudioRecorder {}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late MockAudioRecorder mockRecorder;
  late RecordingService service;

  setUpAll(() {
    registerFallbackValue(const RecordConfig());
  });

  setUp(() {
    mockRecorder = MockAudioRecorder();
    service = RecordingService(recorder: mockRecorder);
    when(() => mockRecorder.dispose()).thenAnswer((_) async {});
  });

  tearDown(() => service.dispose());

  group('RecordingService', () {
    test('constructor works with default AudioRecorder', () async {
      final defaultService = RecordingService();
      await defaultService.dispose();
    });

    test('startRecording starts recording to path', () async {
      when(() => mockRecorder.start(any(), path: any(named: 'path')))
          .thenAnswer((_) async {});
      when(() => mockRecorder.hasPermission())
          .thenAnswer((_) async => true);

      await service.startRecording('/tmp/test.m4a');

      verify(
        () => mockRecorder.start(
          any(),
          path: '/tmp/test.m4a',
        ),
      ).called(1);
    });

    test('startRecording creates missing parent directory', () async {
      final baseDir = await Directory.systemTemp.createTemp('rec_service_');
      try {
        final filePath = '${baseDir.path}/nested/line_0.m4a';
        when(() => mockRecorder.start(any(), path: any(named: 'path')))
            .thenAnswer((_) async {});

        await service.startRecording(filePath);

        expect(Directory('${baseDir.path}/nested').existsSync(), isTrue);
        verify(() => mockRecorder.start(any(), path: filePath)).called(1);
      } finally {
        if (baseDir.existsSync()) {
          await baseDir.delete(recursive: true);
        }
      }
    });

    test('stopRecording stops and returns path', () async {
      when(() => mockRecorder.stop()).thenAnswer((_) async => '/tmp/test.m4a');

      final path = await service.stopRecording();

      expect(path, '/tmp/test.m4a');
    });

    test('hasPermission delegates', () async {
      when(() => mockRecorder.hasPermission())
          .thenAnswer((_) async => true);

      expect(await service.hasPermission(), isTrue);
    });

    test('hasPermission returns false', () async {
      when(() => mockRecorder.hasPermission())
          .thenAnswer((_) async => false);

      expect(await service.hasPermission(), isFalse);
    });

    test('dispose calls recorder dispose', () async {
      when(() => mockRecorder.dispose()).thenAnswer((_) async {});

      await service.dispose();

      verify(() => mockRecorder.dispose()).called(1);
    });
  });
}
