import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/screens/annotation_editor_screen.dart';
import 'package:horatio_app/screens/demo_annotation_editor_screen.dart';
import 'package:horatio_app/widgets/note_chip.dart';
import 'package:horatio_app/widgets/recording_action_bar.dart';
import 'package:shared_preferences/shared_preferences.dart';

late TextScaleCubit _textScaleCubit;

Future<void> _initTextScale() async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  _textScaleCubit = TextScaleCubit(prefs: prefs);
}

Widget _buildDemo() {
  final router = GoRouter(
    initialLocation: '/demo',
    routes: [
      GoRoute(
        path: '/demo',
        builder: (context, state) => DemoAnnotationEditorScreen.withSynthesiser(
          (path, text) async {},
        ),
      ),
      GoRoute(
        path: '/annotation-history',
        builder: (context, state) =>
            const Scaffold(body: Text('History Screen')),
      ),
    ],
  );
  return BlocProvider<TextScaleCubit>.value(
    value: _textScaleCubit,
    child: MaterialApp.router(routerConfig: router),
  );
}

/// Runs a demo screen widget test entirely inside [tester.runAsync].
///
/// [DemoAnnotationEditorScreen] creates a real Drift in-memory database.
/// Drift schedules timers for initial stream data delivery and for cleanup on
/// disposal (via [StreamQueryStore.markAsClosed] when cubits close and cancel
/// stream subscriptions).  Running the full lifecycle — pump, seed wait, cubit
/// init, assertions, and explicit teardown — inside [tester.runAsync] ensures
/// every timer fires in real time and is never left pending as a fake-async
/// timer when the test ends.
Future<void> _runDemoTest(
  WidgetTester tester,
  Future<void> Function() assertions,
) async {
  await tester.runAsync(() async {
    await tester.pumpWidget(_buildDemo());
    // Seeding completes in real time.
    await Future<void>.delayed(const Duration(seconds: 2));
    // Rebuild with _ready = true; creates AnnotationCubit + RecordingCubit
    // which subscribe to Drift streams.
    await tester.pump();
    // Allow Drift's initial stream deliveries to fire in real time.
    await Future<void>.delayed(const Duration(milliseconds: 500));
    // Settle cubit-driven rebuilds.
    await tester.pump();

    await assertions();

    // Teardown inside runAsync so Drift's markAsClosed timers fire in real
    // time rather than as pending fake-async timers.
    await tester.pumpWidget(const SizedBox.shrink());
    await Future<void>.delayed(const Duration(milliseconds: 300));
  });
}

void main() {
  setUpAll(() async {
    await _initTextScale();
  });

  tearDownAll(() => _textScaleCubit.close());

  group('DemoAnnotationEditorScreen', () {
    testWidgets('shows loading indicator while seeding', (tester) async {
      await tester.runAsync(() async {
        await tester.pumpWidget(_buildDemo());
        await tester.pump();
        // Immediately after the first frame, seeding is still in progress.
        expect(find.byType(CircularProgressIndicator), findsOneWidget);

        // Let seeding finish before disposing so the in-flight DB inserts
        // don't hit a closed database.
        await Future<void>.delayed(const Duration(seconds: 2));

        await tester.pumpWidget(const SizedBox.shrink());
        await Future<void>.delayed(const Duration(milliseconds: 300));
      });
    });

    testWidgets('renders AnnotationEditorScreen after seeding', (tester) async {
      await _runDemoTest(tester, () async {
        expect(find.byType(AnnotationEditorScreen), findsOneWidget);
      });
    });

    testWidgets('shows Hamlet title in app bar', (tester) async {
      await _runDemoTest(tester, () async {
        expect(find.textContaining('Hamlet'), findsWidgets);
      });
    });

    testWidgets('shows demo script lines', (tester) async {
      await _runDemoTest(tester, () async {
        expect(
          find.text(
            'To be, or not to be, that is the question:',
            findRichText: true,
          ),
          findsOneWidget,
        );
      });
    });

    testWidgets('tapping a line shows RecordingActionBar', (tester) async {
      await _runDemoTest(tester, () async {
        await tester.tap(
          find.text(
            'To be, or not to be, that is the question:',
            findRichText: true,
          ),
        );
        await tester.pump();

        expect(find.byType(RecordingActionBar), findsOneWidget);
      });
    });

    testWidgets('demo data shows note chips on seeded line', (tester) async {
      await _runDemoTest(tester, () async {
        // Line 3 has two seeded notes (blocking + intention).
        await tester.tap(
          find.text(
            'Or to take arms against a sea of troubles',
            findRichText: true,
          ),
        );
        await tester.pump();

        expect(find.byType(NoteChip), findsWidgets);
      });
    });
  });

  group('synthesiseDemoSpeech', () {
    late Directory tmpDir;

    setUp(() async {
      tmpDir = await Directory.systemTemp.createTemp('horatio_tts_test_');
    });

    tearDown(() async {
      await tmpDir.delete(recursive: true);
    });

    test('espeak-ng fallback: creates a WAV file when piper model is absent',
        () async {
      final path = '${tmpDir.path}/hello.wav';
      // Pass a non-existent model path so the espeak-ng fallback is taken.
      final result = await synthesiseDemoSpeech(
        path,
        'Hello world.',
        piperModel: '${tmpDir.path}/nonexistent.onnx',
      );
      expect(result, path);
      expect(File(path).existsSync(), isTrue);
      expect(File(path).lengthSync(), greaterThan(44)); // has audio data
    });

    test('default piperModel: uses HOME-based model path', () async {
      final path = '${tmpDir.path}/default_model.wav';
      final result = await synthesiseDemoSpeech(path, 'Hello.');
      expect(result, path);
      // Regardless of whether piper or espeak-ng runs, a file is created.
      expect(File(path).existsSync(), isTrue);
    });

    test('piper path: creates a WAV file using the installed model', () async {
      final home = Platform.environment['HOME'] ?? '/root';
      final model =
          '$home/.local/share/horatio/piper/en_US-lessac-high.onnx';
      if (!File(model).existsSync()) {
        // Piper not installed — skip this path on machines without the model.
        return;
      }
      final path = '${tmpDir.path}/hamlet.wav';
      final result = await synthesiseDemoSpeech(
        path,
        'To be.',
        piperModel: model,
      );
      expect(result, path);
      expect(File(path).existsSync(), isTrue);
      expect(File(path).lengthSync(), greaterThan(44));
    });

    test('mobile path: copies bundled asset to destination', () async {
      final path =
          '${tmpDir.path}/hamlet_line0_take1.wav';
      final fakeWav = Uint8List.fromList([
        // Minimal RIFF/WAVE header + 2 bytes of audio data.
        ...utf8.encode('RIFF'),
        50, 0, 0, 0, // chunk size
        ...utf8.encode('WAVE'),
        ...utf8.encode('fmt '),
        16, 0, 0, 0, // sub-chunk size
        1, 0, // PCM
        1, 0, // mono
        0x22, 0x56, 0, 0, // 22050 Hz
        0x44, 0xAC, 0, 0, // byte rate
        2, 0, // block align
        16, 0, // bits per sample
        ...utf8.encode('data'),
        2, 0, 0, 0, // data size
        0, 0, // audio sample
      ]);
      final result = await synthesiseDemoSpeech(
        path,
        'To be, or not to be, that is the question:',
        isMobile: true,
        loadAsset: (_) async =>
            ByteData.sublistView(fakeWav),
      );
      expect(result, path);
      expect(File(path).existsSync(), isTrue);
      expect(File(path).readAsBytesSync(), fakeWav);
    });

    test('mobile path: early return for unknown text', () async {
      final path = '${tmpDir.path}/unknown.wav';
      final result = await synthesiseDemoSpeech(
        path,
        'Unknown line that is not in demoAssetMap',
        isMobile: true,
        loadAsset: (_) async =>
            ByteData.sublistView(Uint8List(0)),
      );
      expect(result, path);
      // File should NOT be created because the text doesn't match any asset.
      expect(File(path).existsSync(), isFalse);
    });
  });

  group('synthesiseDemoSpeechCached', () {
    late Directory tmpDir;

    setUp(() async {
      tmpDir = await Directory.systemTemp.createTemp('horatio_cache_test_');
    });

    tearDown(() async {
      await tmpDir.delete(recursive: true);
    });

    test('synthesises when file does not exist', () async {
      final path = '${tmpDir.path}/new.wav';
      var called = false;
      Future<String> fakeSynth(String p, String t) async {
        called = true;
        await File(p).writeAsBytes([0, 1, 2]); // write something
        return p;
      }

      final result = await synthesiseDemoSpeechCached(
        path,
        'hello',
        synth: fakeSynth,
      );
      expect(result, path);
      expect(called, isTrue);
    });

    test('skips synthesis when file already exists', () async {
      final path = '${tmpDir.path}/existing.wav';
      await File(path).writeAsBytes([0, 1, 2]); // pre-create
      var called = false;
      Future<String> fakeSynth(String p, String t) async {
        called = true;
        return p;
      }

      final result = await synthesiseDemoSpeechCached(
        path,
        'hello',
        synth: fakeSynth,
      );
      expect(result, path);
      expect(called, isFalse); // synthesis was skipped
    });
  });

  group('resolveDemoRecordingsDir', () {
    test('mobile path uses provided getDocsDir', () async {
      final fakeDir = await Directory.systemTemp.createTemp('horatio_docs_');
      addTearDown(() => fakeDir.delete(recursive: true));

      final result = await resolveDemoRecordingsDir(
        isMobile: true,
        getDocsDir: () async => fakeDir,
      );
      expect(result, '${fakeDir.path}/demo_recordings');
    });

    test('desktop path uses HOME environment variable', () async {
      final result = await resolveDemoRecordingsDir(isMobile: false);
      final home = Platform.environment['HOME'] ?? '/root';
      expect(result, '$home/.local/share/horatio/demo_recordings');
    });
  });
}
