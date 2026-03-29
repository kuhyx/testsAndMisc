import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/recording/recording_state.dart';
import 'package:horatio_app/bloc/text_scale/text_scale_cubit.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/screens/annotation_editor_screen.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:horatio_app/widgets/mark_overlay.dart';
import 'package:horatio_app/widgets/mark_selection_toolbar.dart';
import 'package:horatio_app/widgets/note_chip.dart';
import 'package:horatio_app/widgets/recording_action_bar.dart';
import 'package:horatio_app/widgets/recording_badge.dart';
import 'package:horatio_app/widgets/text_scale_settings_sheet.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MockAnnotationDao extends Mock implements AnnotationDao {}

class MockRecordingDao extends Mock implements RecordingDao {}

class MockRecordingService extends Mock implements RecordingService {}

class MockAudioPlaybackService extends Mock implements AudioPlaybackService {}

const _hamlet = Role(name: 'Hamlet');
const _horatio = Role(name: 'Horatio');

Script _testScript() => const Script(
  id: 'editor-screen-test',
  title: 'Test Play',
  roles: [_hamlet, _horatio],
  scenes: [
    Scene(
      lines: [
        ScriptLine(
          text: 'To be or not to be.',
          role: _hamlet,
          sceneIndex: 0,
          lineIndex: 0,
        ),
        ScriptLine(
          text: 'Indeed, my lord.',
          role: _horatio,
          sceneIndex: 0,
          lineIndex: 1,
        ),
      ],
    ),
  ],
);

late MockAnnotationDao _dao;
late MockRecordingDao _recordingDao;
late MockRecordingService _recordingService;
late MockAudioPlaybackService _playbackService;
late StreamController<List<TextMark>> _marksCtrl;
late StreamController<List<LineNote>> _notesCtrl;
late StreamController<List<LineRecording>> _recordingsCtrl;
late StreamController<List<AnnotationSnapshot>> _snapshotsCtrl;
late TextScaleCubit _textScaleCubit;

void _setUpDao() {
  _dao = MockAnnotationDao();
  _marksCtrl = StreamController<List<TextMark>>.broadcast();
  _notesCtrl = StreamController<List<LineNote>>.broadcast();
  _recordingsCtrl = StreamController<List<LineRecording>>.broadcast();
  _snapshotsCtrl = StreamController<List<AnnotationSnapshot>>.broadcast();
  _recordingDao = MockRecordingDao();
  _recordingService = MockRecordingService();
  _playbackService = MockAudioPlaybackService();

  when(
    () => _dao.watchMarksForScript(any()),
  ).thenAnswer((_) => _marksCtrl.stream);
  when(
    () => _dao.watchNotesForScript(any()),
  ).thenAnswer((_) => _notesCtrl.stream);
  when(
    () => _recordingDao.watchRecordingsForScript(any()),
  ).thenAnswer((_) => _recordingsCtrl.stream);
  when(
    () => _dao.watchSnapshotsForScript(any()),
  ).thenAnswer((_) => _snapshotsCtrl.stream);
  when(() => _dao.insertSnapshot(any())).thenAnswer((_) async {});
  when(() => _dao.insertMark(any(), any())).thenAnswer((_) async {});
  when(() => _dao.deleteMark(any())).thenAnswer((_) async {});
  when(() => _dao.insertNote(any(), any())).thenAnswer((_) async {});
  when(() => _dao.deleteNote(any())).thenAnswer((_) async {});
  when(() => _dao.updateNoteText(any(), any())).thenAnswer((_) async {});
  when(() => _dao.updateNoteCategory(any(), any())).thenAnswer((_) async {});

  when(() => _recordingService.hasPermission()).thenAnswer((_) async => true);
  when(() => _recordingService.startRecording(any())).thenAnswer((_) async {});
  when(
    () => _recordingService.stopRecording(),
  ).thenAnswer((_) async => '/tmp/test_recordings/fake.m4a');
  when(
    () => _recordingDao.insertRecording(any(), any()),
  ).thenAnswer((_) async {});
  when(() => _recordingDao.deleteRecording(any())).thenAnswer((_) async {});
  when(
    () => _recordingDao.updateRecordingGrade(any(), any()),
  ).thenAnswer((_) async {});

  when(() => _playbackService.play(any())).thenAnswer((_) async {});
  when(() => _playbackService.stop()).thenAnswer((_) async {});
  when(() => _playbackService.status).thenAnswer((_) => Stream.empty());
  when(() => _playbackService.position).thenAnswer((_) => Stream.empty());
}

Future<void> _initTextScale() async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  _textScaleCubit = TextScaleCubit(prefs: prefs);
}

void _tearDownStreams() {
  _marksCtrl.close();
  _notesCtrl.close();
  _recordingsCtrl.close();
  _snapshotsCtrl.close();
  _textScaleCubit.close();
}

Widget _buildScreen(Script script) => BlocProvider<TextScaleCubit>.value(
  value: _textScaleCubit,
  child: MultiRepositoryProvider(
    providers: [
      RepositoryProvider<AnnotationDao>.value(value: _dao),
      RepositoryProvider<RecordingDao>.value(value: _recordingDao),
      RepositoryProvider<RecordingService>.value(value: _recordingService),
      RepositoryProvider<AudioPlaybackService>.value(value: _playbackService),
      RepositoryProvider<String>.value(value: '/tmp/test_recordings'),
    ],
    child: MaterialApp(home: AnnotationEditorScreen(script: script)),
  ),
);

Widget _buildScreenWithRouter(Script script) {
  final router = GoRouter(
    initialLocation: '/annotations',
    routes: [
      GoRoute(
        path: '/annotations',
        builder: (context, state) => AnnotationEditorScreen(script: script),
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
    child: MultiRepositoryProvider(
      providers: [
        RepositoryProvider<AnnotationDao>.value(value: _dao),
        RepositoryProvider<RecordingDao>.value(value: _recordingDao),
        RepositoryProvider<RecordingService>.value(value: _recordingService),
        RepositoryProvider<AudioPlaybackService>.value(value: _playbackService),
        RepositoryProvider<String>.value(value: '/tmp/test_recordings'),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
}

void main() {
  setUpAll(() {
    registerFallbackValue(
      AnnotationSnapshot(
        id: 'fb',
        scriptId: 'fb',
        timestamp: DateTime.utc(2026),
        marks: const [],
        notes: const [],
      ),
    );
    registerFallbackValue(
      TextMark(
        id: 'fb',
        lineIndex: 0,
        startOffset: 0,
        endOffset: 1,
        type: MarkType.stress,
        createdAt: DateTime.utc(2026),
      ),
    );
    registerFallbackValue(
      LineNote(
        id: 'fb',
        lineIndex: 0,
        category: NoteCategory.general,
        text: 'fb',
        createdAt: DateTime.utc(2026),
      ),
    );
    registerFallbackValue(
      LineRecording(
        id: 'fb-rec',
        scriptId: 'fb-script',
        lineIndex: 0,
        filePath: '/tmp/fb.m4a',
        durationMs: 1000,
        createdAt: DateTime.utc(2026),
      ),
    );
    registerFallbackValue(NoteCategory.general);
  });

  group('AnnotationEditorScreen', () {
    setUp(() async {
      await _initTextScale();
      _setUpDao();
    });
    tearDown(_tearDownStreams);

    testWidgets('shows loading indicator in initial state', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      // Streams haven't emitted yet → AnnotationInitial.
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows script lines after data loads', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      expect(
        find.text('To be or not to be.', findRichText: true),
        findsOneWidget,
      );
      expect(find.text('Indeed, my lord.', findRichText: true), findsOneWidget);
    });

    testWidgets('lines with marks show colored overlay', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([
        TextMark(
          id: 'm1',
          lineIndex: 0,
          startOffset: 0,
          endOffset: 5,
          type: MarkType.stress,
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      // MarkOverlay renders RichText widgets.
      expect(find.byType(RichText), findsWidgets);
      expect(find.text('To be or not to be.'), findsNothing);
    });

    testWidgets('lines with notes show note indicator badge', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'test note',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      expect(find.text('1'), findsOneWidget);
    });

    testWidgets('tapping a line highlights it', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pump();

      // After tap, a Container with primary color should appear.
      final containers = tester
          .widgetList<Container>(find.byType(Container))
          .where((c) => c.color != null);
      expect(containers, isNotEmpty);
    });

    testWidgets('History button is present and navigates', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreenWithRouter(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.history), findsOneWidget);
      await tester.tap(find.byIcon(Icons.history));
      await tester.pumpAndSettle();

      expect(find.text('History Screen'), findsOneWidget);
    });

    testWidgets('selected line shows SelectableText', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      // Tap to select the first line.
      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pump();

      expect(find.byType(SelectableText), findsOneWidget);
    });

    testWidgets('unselected line shows MarkOverlay not SelectableText', (
      tester,
    ) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      // No line selected — should be MarkOverlay.
      expect(find.byType(SelectableText), findsNothing);
      expect(find.byType(MarkOverlay), findsWidgets);
    });

    testWidgets('shows recording action bar when line selected', (
      tester,
    ) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _recordingsCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pumpAndSettle();

      expect(find.byType(RecordingActionBar), findsOneWidget);
      expect(find.byIcon(Icons.mic), findsOneWidget);
    });

    testWidgets('hides recording action bar when no line selected', (
      tester,
    ) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _recordingsCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      expect(find.byType(RecordingActionBar), findsNothing);
    });

    testWidgets('recording action bar record and stop invoke services', (
      tester,
    ) async {
      final script = _testScript();
      when(
        () => _recordingDao.watchRecordingsForScript(any()),
      ).thenAnswer((_) => Stream.value([]));
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.mic));
      await tester.pump();

      verify(() => _recordingService.startRecording(any())).called(1);
      expect(find.byIcon(Icons.stop), findsOneWidget);

      await tester.tap(find.byIcon(Icons.stop));
      await tester.pumpAndSettle();

      verify(() => _recordingService.stopRecording()).called(1);
      verify(() => _recordingDao.insertRecording(any(), any())).called(1);
    });

    testWidgets('recording action bar play uses latest recording', (
      tester,
    ) async {
      final script = _testScript();
      when(() => _recordingDao.watchRecordingsForScript(any())).thenAnswer(
        (_) => Stream.value([
          LineRecording(
            id: 'r1',
            scriptId: 'editor-screen-test',
            lineIndex: 0,
            filePath: '/tmp/rec.m4a',
            durationMs: 5000,
            createdAt: DateTime.utc(2026),
          ),
        ]),
      );

      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithIcon(IconButton, Icons.play_arrow));
      await tester.pumpAndSettle();

      verify(() => _playbackService.play('/tmp/rec.m4a')).called(1);
    });

    testWidgets('shows note chips for selected line', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.general,
          text: 'A test note',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _recordingsCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pumpAndSettle();

      expect(find.byType(NoteChip), findsOneWidget);
      expect(find.text('A test note'), findsOneWidget);
    });

    testWidgets('recording badge shows count for line', (tester) async {
      final script = _testScript();
      when(() => _recordingDao.watchRecordingsForScript(any())).thenAnswer(
        (_) => Stream.value([
          LineRecording(
            id: 'r1',
            scriptId: 'editor-screen-test',
            lineIndex: 0,
            filePath: '/tmp/rec.m4a',
            durationMs: 5000,
            createdAt: DateTime.utc(2026),
          ),
        ]),
      );
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      expect(find.byType(RecordingBadge), findsNWidgets(2));
      final badges = tester.widgetList<RecordingBadge>(
        find.byType(RecordingBadge),
      );
      expect(badges.any((badge) => badge.recordingCount == 1), isTrue);
      expect(find.text('1'), findsOneWidget);
    });

    testWidgets('tapping recording badge opens list and plays recording', (
      tester,
    ) async {
      final script = _testScript();
      when(() => _recordingDao.watchRecordingsForScript(any())).thenAnswer(
        (_) => Stream.value([
          LineRecording(
            id: 'r1',
            scriptId: 'editor-screen-test',
            lineIndex: 0,
            filePath: '/tmp/rec.m4a',
            durationMs: 5000,
            createdAt: DateTime.utc(2026),
          ),
        ]),
      );

      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('1').first);
      await tester.pumpAndSettle();

      expect(find.text('Recordings'), findsOneWidget);

      await tester.tap(find.byIcon(Icons.play_arrow).first);
      await tester.pumpAndSettle();

      verify(() => _playbackService.play('/tmp/rec.m4a')).called(1);
    });

    testWidgets('recording list grade and delete actions call dao', (
      tester,
    ) async {
      final script = _testScript();
      when(() => _recordingDao.watchRecordingsForScript(any())).thenAnswer(
        (_) => Stream.value([
          LineRecording(
            id: 'r1',
            scriptId: 'editor-screen-test',
            lineIndex: 0,
            filePath: '/tmp/rec.m4a',
            durationMs: 5000,
            createdAt: DateTime.utc(2026),
          ),
        ]),
      );

      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('1').first);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Blackout').first);
      await tester.pumpAndSettle();

      verify(() => _recordingDao.updateRecordingGrade('r1', 0)).called(1);

      await tester.tap(find.byIcon(Icons.delete).first);
      await tester.pumpAndSettle();

      verify(() => _recordingDao.deleteRecording('r1')).called(1);
    });

    testWidgets('long-press note chip calls removeNote', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      final note = LineNote(
        id: 'n-del',
        lineIndex: 0,
        category: NoteCategory.general,
        text: 'Delete me',
        createdAt: DateTime.utc(2026),
      );

      _marksCtrl.add([]);
      _notesCtrl.add([note]);
      _recordingsCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pumpAndSettle();

      await tester.longPress(find.byType(NoteChip));
      await tester.pumpAndSettle();

      verify(() => _dao.deleteNote('n-del')).called(1);
    });

    testWidgets('tapping note chip opens editor and saves updates', (
      tester,
    ) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'old text',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _recordingsCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(NoteChip));
      await tester.pumpAndSettle();

      expect(find.text('old text'), findsWidgets);

      await tester.enterText(find.byType(TextFormField), 'new text');
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      verify(() => _dao.updateNoteText('n1', 'new text')).called(1);
      verify(
        () => _dao.updateNoteCategory('n1', NoteCategory.intention),
      ).called(1);
    });

    testWidgets('tapping add-note icon opens note editor', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _recordingsCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.note_add_outlined).first);
      await tester.pumpAndSettle();

      expect(find.text('Category'), findsOneWidget);
      expect(find.text('Save'), findsOneWidget);
    });

    testWidgets('editing note sheet cancel dismisses without updates', (
      tester,
    ) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'old text',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _recordingsCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(NoteChip));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      verifyNever(() => _dao.updateNoteText(any(), any()));
      verifyNever(() => _dao.updateNoteCategory(any(), any()));
    });

    testWidgets('text selection shows toolbar and applies selected mark', (
      tester,
    ) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pump();

      final selectable = tester.widget<SelectableText>(
        find.byType(SelectableText),
      );
      selectable.onSelectionChanged!(
        const TextSelection(baseOffset: 0, extentOffset: 5),
        SelectionChangedCause.tap,
      );
      await tester.pump();

      expect(find.byType(MarkSelectionToolbar), findsOneWidget);
      await tester.tap(find.text('Stress'));
      await tester.pumpAndSettle();

      verify(() => _dao.insertMark(any(), any())).called(1);
      expect(find.byType(MarkSelectionToolbar), findsNothing);
    });

    testWidgets('collapsed selection does not show toolbar', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pump();

      final selectable = tester.widget<SelectableText>(
        find.byType(SelectableText),
      );
      selectable.onSelectionChanged!(
        const TextSelection.collapsed(offset: 0),
        SelectionChangedCause.tap,
      );
      await tester.pump();

      expect(find.byType(MarkSelectionToolbar), findsNothing);
    });

    testWidgets('switching selected line removes toolbar overlay', (
      tester,
    ) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pump();

      final selectable = tester.widget<SelectableText>(
        find.byType(SelectableText),
      );
      selectable.onSelectionChanged!(
        const TextSelection(baseOffset: 0, extentOffset: 5),
        SelectionChangedCause.tap,
      );
      await tester.pump();
      expect(find.byType(MarkSelectionToolbar), findsOneWidget);

      await tester.tap(find.text('Indeed, my lord.', findRichText: true));
      await tester.pumpAndSettle();

      expect(find.byType(MarkSelectionToolbar), findsNothing);
    });

    testWidgets('selected line supports marks with unmarked prefix', (
      tester,
    ) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      final mark = TextMark(
        id: 'prefix-mark',
        lineIndex: 0,
        startOffset: 2,
        endOffset: 7,
        type: MarkType.stress,
        createdAt: DateTime.utc(2026),
      );
      _marksCtrl.add([mark]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pump();

      expect(find.byType(SelectableText), findsOneWidget);
    });

    testWidgets('tapping a marked span shows remove dialog and No dismisses', (
      tester,
    ) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      final mark = TextMark(
        id: 'm1',
        lineIndex: 0,
        startOffset: 0,
        endOffset: 5,
        type: MarkType.stress,
        createdAt: DateTime.utc(2026),
      );
      _marksCtrl.add([mark]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      // Tap the line to select it.
      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pump();

      // Tap the colored span area to trigger mark removal dialog.
      final textTopLeft = tester.getTopLeft(find.byType(SelectableText));
      await tester.tapAt(textTopLeft + const Offset(24, 12));
      await tester.pump();

      expect(find.text('Remove mark?'), findsOneWidget);
      await tester.tap(find.text('No'));
      await tester.pumpAndSettle();

      verifyNever(() => _dao.deleteMark(any()));
      expect(find.text('Remove mark?'), findsNothing);
    });

    testWidgets('confirming remove dialog calls removeMark', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      final mark = TextMark(
        id: 'm1',
        lineIndex: 0,
        startOffset: 0,
        endOffset: 5,
        type: MarkType.stress,
        createdAt: DateTime.utc(2026),
      );
      _marksCtrl.add([mark]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('To be or not to be.', findRichText: true));
      await tester.pump();

      final textTopLeft = tester.getTopLeft(find.byType(SelectableText));
      await tester.tapAt(textTopLeft + const Offset(24, 12));
      await tester.pump();

      expect(find.text('Remove mark?'), findsOneWidget);
      await tester.tap(find.text('Yes'));
      await tester.pumpAndSettle();

      verify(() => _dao.deleteMark('m1')).called(1);
    });

    testWidgets('tapping note indicator shows note editor sheet', (
      tester,
    ) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'existing note',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('1'));
      await tester.pumpAndSettle();

      expect(find.text('Category'), findsOneWidget);
      expect(find.text('Save'), findsOneWidget);
    });

    testWidgets('saving note in editor calls addNote', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'existing note',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('1'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), 'New note text');
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      verify(() => _dao.insertNote(any(), any())).called(1);
    });

    testWidgets('cancel in note editor sheet dismisses', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'existing note',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('1'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      expect(find.text('Category'), findsNothing);
    });

    testWidgets('FAB saves snapshot', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      verify(() => _dao.insertSnapshot(any())).called(1);
    });

    testWidgets('FAB hidden in initial state', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      // Streams haven't emitted → initial state.
      expect(find.byType(FloatingActionButton), findsNothing);
    });

    testWidgets('AppBar shows script title', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      expect(find.text('Annotate: Test Play'), findsOneWidget);
    });

    testWidgets('text size button opens settings sheet', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.text_fields));
      await tester.pumpAndSettle();
      expect(find.byType(TextScaleSettingsSheet), findsOneWidget);
    });
  });
}
