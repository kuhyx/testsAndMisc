import 'dart:io';

import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/screens/annotation_editor_screen.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:horatio_core/horatio_core.dart';
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
  const DemoAnnotationEditorScreen({super.key});

  @override
  State<DemoAnnotationEditorScreen> createState() =>
      _DemoAnnotationEditorScreenState();
}

class _DemoAnnotationEditorScreenState
    extends State<DemoAnnotationEditorScreen> {
  late final AppDatabase _db;
  late final RecordingService _recordingService;
  late final AudioPlaybackService _playbackService;
  final String _recordingsDir =
      '${Directory.systemTemp.path}/horatio_demo_recordings';

  bool _ready = false;

  @override
  void initState() {
    super.initState();
    _db = AppDatabase(NativeDatabase.memory());
    _recordingService = RecordingService();
    _playbackService = AudioPlaybackService();
    _seedAndMarkReady();
  }

  Future<void> _seedAndMarkReady() async {
    await _seed(_db.annotationDao, _db.recordingDao);
    if (mounted) setState(() => _ready = true);
  }

  @override
  void dispose() {
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

/// Seeds the in-memory DAOs with a realistic demo dataset.
Future<void> _seed(AnnotationDao dao, RecordingDao rDao) async {
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

  // ── Recordings (metadata only — paths are illustrative) ─────────────────
  // Line 0: three recordings showing progression.
  await rDao.insertRecording(
    scriptId,
    LineRecording(
      id: _uuid.v4(),
      scriptId: scriptId,
      lineIndex: 0,
      filePath: '/demo/hamlet_line0_take1.m4a',
      durationMs: 9800,
      createdAt: week1,
      grade: 2,
    ),
  );
  await rDao.insertRecording(
    scriptId,
    LineRecording(
      id: _uuid.v4(),
      scriptId: scriptId,
      lineIndex: 0,
      filePath: '/demo/hamlet_line0_take2.m4a',
      durationMs: 8400,
      createdAt: week2,
      grade: 4,
    ),
  );
  await rDao.insertRecording(
    scriptId,
    LineRecording(
      id: _uuid.v4(),
      scriptId: scriptId,
      lineIndex: 0,
      filePath: '/demo/hamlet_line0_take3.m4a',
      durationMs: 7600,
      createdAt: week3,
      grade: 5,
    ),
  );
  // Line 1: one recording.
  await rDao.insertRecording(
    scriptId,
    LineRecording(
      id: _uuid.v4(),
      scriptId: scriptId,
      lineIndex: 1,
      filePath: '/demo/hamlet_line1_take1.m4a',
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
