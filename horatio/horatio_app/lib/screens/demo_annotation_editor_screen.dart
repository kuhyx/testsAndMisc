import 'dart:io';

import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show ByteData, rootBundle;
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/screens/annotation_editor_screen.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

const _uuid = Uuid();
const _scriptId = 'demo-hamlet-soliloquy';
const _hamlet = Role(name: 'Hamlet');

/// Demo script — Hamlet's soliloquy (6 lines).
const _demoScript = Script(
  id: _scriptId,
  title: 'Hamlet — To be, or not to be (demo)',
  roles: [_hamlet],
  scenes: [
    Scene(
      title: 'Act III, Scene I',
      lines: [
        ScriptLine(
          text: 'To be, or not to be, that is the question:',
          role: _hamlet,
          sceneIndex: 0,
          lineIndex: 0,
        ),
        ScriptLine(
          text: "Whether 'tis nobler in the mind to suffer",
          role: _hamlet,
          sceneIndex: 0,
          lineIndex: 1,
        ),
        ScriptLine(
          text: 'The slings and arrows of outrageous fortune,',
          role: _hamlet,
          sceneIndex: 0,
          lineIndex: 2,
        ),
        ScriptLine(
          text: 'Or to take arms against a sea of troubles',
          role: _hamlet,
          sceneIndex: 0,
          lineIndex: 3,
        ),
        ScriptLine(
          text: 'And by opposing end them.',
          role: _hamlet,
          sceneIndex: 0,
          lineIndex: 4,
        ),
        ScriptLine(
          text: 'To die: to sleep; no more;',
          role: _hamlet,
          sceneIndex: 0,
          lineIndex: 5,
        ),
      ],
    ),
  ],
);

/// Wraps [AnnotationEditorScreen] with a fully in-memory database seeded with
/// realistic demo annotations, notes, and recordings.
///
/// All data lives only in RAM — nothing is written to disk or the real DB.
/// The demo is fully interactive: users can add/edit marks and notes while
/// exploring the screen.
class DemoAnnotationEditorScreen extends StatefulWidget {
  /// Creates a [DemoAnnotationEditorScreen].
  const DemoAnnotationEditorScreen({super.key})
      : _syntheseFn = null;

  /// Constructor used in tests to inject a fast no-op speech synthesiser,
  /// avoiding the slow Piper TTS process during widget tests.
  @visibleForTesting
  const DemoAnnotationEditorScreen.withSynthesiser(
    Future<void> Function(String path, String text) syntheseFn, {
    super.key,
  }) : _syntheseFn = syntheseFn;

  // Null means use the default [synthesiseDemoSpeech] implementation.
  final Future<void> Function(String path, String text)? _syntheseFn;

  @override
  State<DemoAnnotationEditorScreen> createState() =>
      _DemoAnnotationEditorScreenState();
}

class _DemoAnnotationEditorScreenState
    extends State<DemoAnnotationEditorScreen> {
  late final AppDatabase _db;
  late final RecordingService _recordingService;
  late final AudioPlaybackService _playbackService;
  String _recordingsDir = '';

  bool _ready = false;
  bool _disposed = false;

  @override
  void initState() {
    super.initState();
    _db = AppDatabase(NativeDatabase.memory());
    _recordingService = RecordingService();
    _playbackService = AudioPlaybackService();
    _seedAndMarkReady();
  }

  Future<void> _seedAndMarkReady() async {
    _recordingsDir = await resolveDemoRecordingsDir();
    await _seed(
      _db.annotationDao,
      _db.recordingDao,
      _recordingsDir,
      () => _disposed,
      speechSynthesiser: widget._syntheseFn,
    );
    if (mounted) setState(() => _ready = true);
  }

  @override
  void dispose() {
    _disposed = true;
    _db.close();
    _recordingService.dispose();
    _playbackService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_ready) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return MultiRepositoryProvider(
      providers: [
        RepositoryProvider<AnnotationDao>.value(value: _db.annotationDao),
        RepositoryProvider<RecordingDao>.value(value: _db.recordingDao),
        RepositoryProvider<RecordingService>.value(value: _recordingService),
        RepositoryProvider<AudioPlaybackService>.value(value: _playbackService),
        RepositoryProvider<String>.value(value: _recordingsDir),
      ],
      child: const AnnotationEditorScreen(script: _demoScript),
    );
  }
}

/// Resolves the demo recordings directory, using path_provider on mobile.
@visibleForTesting
Future<String> resolveDemoRecordingsDir({
  bool? isMobile,
  Future<Directory> Function()? getDocsDir,
}) async {
  if (isMobile ?? (Platform.isAndroid || Platform.isIOS)) {
    final dir = await (getDocsDir ?? getApplicationDocumentsDirectory)();
    return '${dir.path}/demo_recordings';
  }
  return '${Platform.environment['HOME']}/.local/share/horatio/demo_recordings';
}

/// Map from WAV filename to the demo line text it represents.
///
/// Used on Android/iOS to look up the correct bundled asset for a given
/// line of text, and on desktop to decide whether to synthesise or copy.
@visibleForTesting
const demoAssetMap = <String, String>{
  'hamlet_line0_take1.wav': 'To be, or not to be, that is the question:',
  'hamlet_line0_take2.wav': 'To be, or not to be, that is the question:',
  'hamlet_line0_take3.wav': 'To be, or not to be, that is the question:',
  'hamlet_line1_take1.wav': "Whether 'tis nobler in the mind to suffer",
};

/// Reverse lookup: text → list of bundled asset filenames.
Map<String, List<String>> _textToAssets() {
  final map = <String, List<String>>{};
  for (final entry in demoAssetMap.entries) {
    map.putIfAbsent(entry.value, () => []).add(entry.key);
  }
  return map;
}

/// Counter used to pick the next bundled asset for a given line of text.
int _assetCounter = 0;

/// Synthesises [text] to a WAV file at [path] and returns [path].
///
/// On Android/iOS, copies a pre-generated WAV from the bundled Flutter assets
/// so the demo works reliably regardless of TTS engine availability.
///
/// On desktop, uses Piper TTS (neural, high-quality English voice) when the
/// model file at [piperModel] exists.  Falls back to `espeak-ng` otherwise
/// (always available on the dev machine).
///
/// Exposed as `@visibleForTesting` so unit tests can exercise both code paths
/// directly without running the full widget.
@visibleForTesting
Future<String> synthesiseDemoSpeech(
  String path,
  String text, {
  String? piperModel,
  bool? isMobile,
  Future<ByteData> Function(String key)? loadAsset,
}) async {
  final effectiveLoadAsset = loadAsset ?? rootBundle.load;
  if (isMobile ?? (Platform.isAndroid || Platform.isIOS)) {
    await _copyBundledAsset(path, text, loadAsset: effectiveLoadAsset);
    return path;
  }
  final model =
      piperModel ??
          '${Platform.environment['HOME']}/.local/share/horatio/piper/en_US-lessac-high.onnx';
  if (File(model).existsSync()) {
    final process = await Process.start(
      'python3',
      ['-m', 'piper', '--model', model, '--output_file', path],
    );
    process.stdin.write(text);
    await process.stdin.close();
    await process.exitCode;
  } else {
    await Process.run('espeak-ng', ['--punct', '-w', path, text]);
  }
  return path;
}

/// Copies a pre-generated WAV from Flutter assets to [path].
Future<void> _copyBundledAsset(
  String path,
  String text, {
  required Future<ByteData> Function(String key) loadAsset,
}) async {
  final assets = _textToAssets()[text];
  if (assets == null || assets.isEmpty) return;
  final asset = assets[_assetCounter++ % assets.length];
  final data = await loadAsset('assets/demo_recordings/$asset');
  await File(path).writeAsBytes(
    data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes),
  );
}

/// Synthesises [text] to a WAV file at [path], skipping synthesis if the
/// file already exists on disk.
///
/// Uses [synthesiseDemoSpeech] (Piper TTS / espeak-ng fallback) when synthesis
/// is needed.  Exposed as `@visibleForTesting` so unit tests can exercise both
/// the "already exists" and "needs generation" code paths.
@visibleForTesting
Future<String> synthesiseDemoSpeechCached(
  String path,
  String text, {
  Future<void> Function(String, String)? synth,
}) async {
  if (!File(path).existsSync()) {
    await (synth ?? synthesiseDemoSpeech)(path, text);
  }
  return path;
}


/// Seeds the in-memory DAOs with a realistic demo dataset.
///
/// Synthesises speech for each recording using [speechSynthesiser] when
/// provided, otherwise falls back to the default [synthesiseDemoSpeech].
///
/// [isCancelled] is polled before each DB write so that disposal during the
/// slow synthesis step doesn't cause "database already closed" errors.
Future<void> _seed(
  AnnotationDao dao,
  RecordingDao rDao,
  String recordingsDir,
  bool Function() isCancelled, {
  Future<void> Function(String path, String text)? speechSynthesiser,
}) async {
  await Directory(recordingsDir).create(recursive: true);
  const scriptId = _scriptId;
  final week1 = DateTime.utc(2026, 1, 15, 19);
  final week2 = DateTime.utc(2026, 1, 22, 20);
  final week3 = DateTime.utc(2026, 2, 1, 18);
  final now = DateTime.utc(2026, 3, 15, 21);

  // ── Text marks ──────────────────────────────────────────────────────────
  // Collect marks as we insert them so the snapshot doesn't need stream reads.
  final marks = <TextMark>[];

  TextMark newMark({
    required int lineIndex,
    required int startOffset,
    required int endOffset,
    required MarkType type,
    required DateTime createdAt,
  }) => TextMark(
    id: _uuid.v4(),
    lineIndex: lineIndex,
    startOffset: startOffset,
    endOffset: endOffset,
    type: type,
    createdAt: createdAt,
  );

  // Line 0: stress "To be" + slow down the question;
  // Line 2: emphasis on "slings and arrows";
  // Line 4: breath before ending.
  marks
    ..add(
      newMark(
        lineIndex: 0,
        startOffset: 0,
        endOffset: 5,
        type: MarkType.stress,
        createdAt: week1,
      ),
    )
    ..add(
      newMark(
        lineIndex: 0,
        startOffset: 16,
        endOffset: 43,
        type: MarkType.slowDown,
        createdAt: week2,
      ),
    )
    ..add(
      newMark(
        lineIndex: 2,
        startOffset: 4,
        endOffset: 20,
        type: MarkType.emphasis,
        createdAt: week1,
      ),
    )
    ..add(
      newMark(
        lineIndex: 4,
        startOffset: 0,
        endOffset: 13,
        type: MarkType.breath,
        createdAt: week3,
      ),
    );
  for (final m in marks) {
    await dao.insertMark(scriptId, m);
  }

  // ── Line notes ──────────────────────────────────────────────────────────
  final notes = <LineNote>[];

  LineNote newNote({
    required int lineIndex,
    required NoteCategory category,
    required String text,
    required DateTime createdAt,
  }) => LineNote(
    id: _uuid.v4(),
    lineIndex: lineIndex,
    category: category,
    text: text,
    createdAt: createdAt,
  );

  notes
    ..add(
      newNote(
        lineIndex: 1,
        category: NoteCategory.delivery,
        text: 'Breathe slowly before this line — let the weight land',
        createdAt: week1,
      ),
    )
    ..add(
      newNote(
        lineIndex: 3,
        category: NoteCategory.blocking,
        text: 'Step downstage, half-turn to audience on "Or to take arms"',
        createdAt: week2,
      ),
    )
    ..add(
      newNote(
        lineIndex: 3,
        category: NoteCategory.intention,
        text: 'He has already decided — resignation, not a genuine question',
        createdAt: week3,
      ),
    )
    ..add(
      newNote(
        lineIndex: 0,
        category: NoteCategory.subtext,
        text: "Staring at nothing. The audience exists; he doesn't see them",
        createdAt: now,
      ),
    );
  for (final n in notes) {
    await dao.insertNote(scriptId, n);
  }

  // ── Recordings — Piper TTS speech (falls back to espeak-ng) ─────────────
  final synthFn = speechSynthesiser ?? synthesiseDemoSpeech;

  Future<String> writeSpeech(String name, String text) async {
    final path = '$recordingsDir/$name';
    return synthesiseDemoSpeechCached(path, text, synth: synthFn);
  }

  const line0 = 'To be, or not to be, that is the question:';
  const line1 = "Whether 'tis nobler in the mind to suffer";

  // Line 0: three takes showing progression (same text, recurring practice).
  final take1path = await writeSpeech('hamlet_line0_take1.wav', line0);
  if (isCancelled()) return;
  await rDao.insertRecording(
    scriptId,
    LineRecording(
      id: _uuid.v4(),
      scriptId: scriptId,
      lineIndex: 0,
      filePath: take1path,
      durationMs: 9800,
      createdAt: week1,
      grade: 2,
    ),
  );
  final take2path = await writeSpeech('hamlet_line0_take2.wav', line0);
  if (isCancelled()) return;
  await rDao.insertRecording(
    scriptId,
    LineRecording(
      id: _uuid.v4(),
      scriptId: scriptId,
      lineIndex: 0,
      filePath: take2path,
      durationMs: 8400,
      createdAt: week2,
      grade: 4,
    ),
  );
  final take3path = await writeSpeech('hamlet_line0_take3.wav', line0);
  if (isCancelled()) return;
  await rDao.insertRecording(
    scriptId,
    LineRecording(
      id: _uuid.v4(),
      scriptId: scriptId,
      lineIndex: 0,
      filePath: take3path,
      durationMs: 7600,
      createdAt: week3,
      grade: 5,
    ),
  );
  // Line 1: one take.
  final take4path = await writeSpeech('hamlet_line1_take1.wav', line1);
  if (isCancelled()) return;
  await rDao.insertRecording(
    scriptId,
    LineRecording(
      id: _uuid.v4(),
      scriptId: scriptId,
      lineIndex: 1,
      filePath: take4path,
      durationMs: 6200,
      createdAt: week2,
      grade: 3,
    ),
  );

  // ── Annotation snapshot (history entry from week 1) ──────────────────────
  // Use the already-collected marks/notes — no stream reads needed.
  await dao.insertSnapshot(
    AnnotationSnapshot(
      id: _uuid.v4(),
      scriptId: scriptId,
      timestamp: week1,
      marks: marks,
      notes: notes,
    ),
  );
}
