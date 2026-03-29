## Chunk 6: Screen Integration + Providers + Final Pipeline

### Task 6.1: Add RecordingDao + services to app.dart

**Files:**

- Modify: `horatio_app/lib/app.dart`
- Modify: `horatio_app/test/app_test.dart`

- [ ] **Step 1: Update app.dart providers**

Add `RecordingDao`, `RecordingService`, and `AudioPlaybackService` as `RepositoryProvider`s:

```dart
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';
```

In `MultiRepositoryProvider.providers`, add:

```dart
RepositoryProvider<RecordingDao>(
  create: (_) => database.recordingDao,
),
RepositoryProvider<RecordingService>(
  create: (_) => RecordingService(),
  dispose: (service) => service.dispose(),
),
RepositoryProvider<AudioPlaybackService>(
  create: (_) => AudioPlaybackService(),
  dispose: (service) => service.dispose(),
),
```

The `HoratioApp` constructor must accept a `recordingsDir` parameter (String):

```dart
class HoratioApp extends StatelessWidget {
  const HoratioApp({
    required this.database,
    required this.recordingsDir,
    super.key,
  });

  final AppDatabase database;
  final String recordingsDir;
```

And add the recordings dir to the `MultiRepositoryProvider.providers` list so screens can access it:

```dart
RepositoryProvider<String>.value(value: recordingsDir),
```

In `main.dart`, pass `recordingsDir` from `path_provider`:

```dart
final appDocDir = await getApplicationDocumentsDirectory();
final recordingsDir = '${appDocDir.path}/horatio_recordings';
// ...
HoratioApp(database: database, recordingsDir: recordingsDir),
```

Note: `RepositoryProvider` in flutter_bloc ^9.0.0 supports the `dispose` parameter — this is confirmed in the official docs and the constructor signature: `RepositoryProvider({required T create(BuildContext), void dispose(T)?, ...})`.

- [ ] **Step 2: Update app_test.dart**

Add mock classes for the new dependencies and wire them into the test builders:

```dart
class MockRecordingDao extends Mock implements RecordingDao {}
class MockRecordingService extends Mock implements RecordingService {}
class MockAudioPlaybackService extends Mock implements AudioPlaybackService {}
```

In `_buildScreen` and `_buildScreenWithRouter`, wrap with the new `RepositoryProvider`s:

```dart
Widget _buildScreen(Script script) => MultiRepositoryProvider(
      providers: [
        RepositoryProvider<ScriptRepository>.value(value: _scriptRepo),
        RepositoryProvider<AnnotationDao>.value(value: _annotationDao),
        RepositoryProvider<RecordingDao>.value(value: _recordingDao),
        RepositoryProvider<RecordingService>.value(value: _recordingService),
        RepositoryProvider<AudioPlaybackService>.value(
          value: _playbackService,
        ),
      ],
      child: MaterialApp(home: HoratioApp(database: _database)),
    );
```

Existing tests should still pass since the new providers are lazy (only created on first access).

- [ ] **Step 3: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/app_test.dart -v
```

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/app.dart horatio_app/test/app_test.dart
git commit -m "feat(app): add RecordingDao and audio services to providers"
```

---

### Task 6.2: Integrate recording + note chips into AnnotationEditorScreen

**Files:**

- Modify: `horatio_app/lib/screens/annotation_editor_screen.dart`
- Modify: `horatio_app/test/screens/annotation_editor_screen_test.dart`

- [ ] **Step 1: Add RecordingCubit provider to AnnotationEditorScreen**

In the `AnnotationEditorScreen.build` method, add `RecordingCubit` to the `MultiBlocProvider`. Also pass `recordingsDir` — the `HoratioApp` (in `app.dart`) must pass the documents directory path down. For simplicity, read it from a `RepositoryProvider<String>` keyed by a typedef:

In `app.dart`, add the recordings dir as a named provider (added in Task 6.1):

```dart
RepositoryProvider<String>.value(
  value: recordingsDir, // passed from main.dart
),
```

In `AnnotationEditorScreen.build`, update the `MultiBlocProvider.providers` list:

```dart
BlocProvider(
  create: (context) => RecordingCubit(
    dao: context.read<RecordingDao>(),
    recordingService: context.read<RecordingService>(),
    playbackService: context.read<AudioPlaybackService>(),
    recordingsDir: context.read<String>(),
  )..loadRecordings(script.id),
),
```

Add these imports at the top of `annotation_editor_screen.dart`:

```dart
import 'package:horatio_app/bloc/recording/recording_cubit.dart';
import 'package:horatio_app/bloc/recording/recording_state.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:horatio_app/widgets/note_chip.dart';
import 'package:horatio_app/widgets/recording_action_bar.dart';
import 'package:horatio_app/widgets/recording_badge.dart';
import 'package:horatio_app/widgets/recording_list_sheet.dart';
```

- [ ] **Step 2: Add RecordingActionBar below the line list**

Replace `_AnnotationEditorBody.build`'s `body:` parameter — swap the bare `BlocBuilder` with a `Column` containing both the line list and a conditional `RecordingActionBar`:

```dart
        body: BlocBuilder<AnnotationCubit, AnnotationState>(
          builder: (context, annotationState) => switch (annotationState) {
            AnnotationInitial() =>
              const Center(child: CircularProgressIndicator()),
            AnnotationLoaded() => Column(
                children: [
                  Expanded(child: _buildLineList(context, annotationState)),
                  if (annotationState.selectedLineIndex != null)
                    BlocBuilder<RecordingCubit, RecordingState>(
                      builder: (context, recState) {
                        final lineIndex =
                            annotationState.selectedLineIndex!;
                        final isRecording = recState is RecordingInProgress &&
                            recState.lineIndex == lineIndex;
                        final elapsed =
                            isRecording ? recState.elapsed : Duration.zero;
                        final recordings = recState.recordings
                            .where((r) => r.lineIndex == lineIndex)
                            .toList();
                        return RecordingActionBar(
                          isRecording: isRecording,
                          elapsed: elapsed,
                          latestRecording:
                              recordings.isNotEmpty ? recordings.last : null,
                          onRecord: () => context
                              .read<RecordingCubit>()
                              .startRecording(script.id, lineIndex),
                          onStop: () =>
                              context.read<RecordingCubit>().stopRecording(),
                          onPlay: () {
                            if (recordings.isNotEmpty) {
                              context
                                  .read<RecordingCubit>()
                                  .playRecording(recordings.last);
                            }
                          },
                        );
                      },
                    ),
                ],
              ),
          },
        ),
```

- [ ] **Step 3: Add NoteChips and RecordingBadge to \_LineTile**

Replace the `_LineTile.build` method's `child: Padding(...)` with a `Column` containing both the existing content and a conditional `Wrap` of `NoteChip` widgets when the line is selected:

```dart
  @override
  Widget build(BuildContext context) => Container(
        color: widget.isSelected
            ? Theme.of(context).colorScheme.primaryContainer.withValues(
                  alpha: 0.3,
                )
            : null,
        child: InkWell(
          onTap: () =>
              context.read<AnnotationCubit>().selectLine(widget.lineIndex),
          onLongPress: () => _showMarkPicker(context),
          child: Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: widget.isSelected
                          ? _SelectableMarkOverlay(
                              text: widget.line.text,
                              marks: widget.marks,
                              lineIndex: widget.lineIndex,
                            )
                          : MarkOverlay(
                              text: widget.line.text,
                              marks: widget.marks,
                            ),
                    ),
                    BlocBuilder<RecordingCubit, RecordingState>(
                      builder: (context, recState) {
                        final count = recState.recordings
                            .where((r) => r.lineIndex == widget.lineIndex)
                            .length;
                        return RecordingBadge(
                          recordingCount: count,
                          onTap: () => _showRecordingList(
                            context,
                            recState.recordings
                                .where(
                                  (r) => r.lineIndex == widget.lineIndex,
                                )
                                .toList(),
                          ),
                        );
                      },
                    ),
                    NoteIndicator(
                      noteCount: widget.notes.length,
                      onTap: () => _showNoteEditor(context),
                    ),
                  ],
                ),
                if (widget.isSelected && widget.notes.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Wrap(
                      spacing: 4,
                      runSpacing: 4,
                      children: widget.notes
                          .map(
                            (note) => NoteChip(
                              note: note,
                              onTap: () =>
                                  _showNoteEditorForEdit(context, note),
                              onDelete: () => context
                                  .read<AnnotationCubit>()
                                  .removeNote(note.id),
                            ),
                          )
                          .toList(),
                    ),
                  ),
              ],
            ),
          ),
        ),
      );
```

Add a helper to show the recording list bottom sheet:

```dart
  void _showRecordingList(
    BuildContext context,
    List<LineRecording> recordings,
  ) {
    showModalBottomSheet<void>(
      context: context,
      builder: (_) => RecordingListSheet(
        recordings: recordings,
        onPlay: (recording) {
          Navigator.pop(context);
          context.read<RecordingCubit>().playRecording(recording);
        },
        onGrade: (id, grade) =>
            context.read<RecordingCubit>().gradeRecording(id, grade),
        onDelete: (id) =>
            context.read<RecordingCubit>().deleteRecording(id),
      ),
    );
  }

  void _showNoteEditorForEdit(BuildContext context, LineNote note) {
    final cubit = context.read<AnnotationCubit>();
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: NoteEditorSheet(
          initialCategory: note.category,
          initialText: note.text,
          noteId: note.id,
          onSave: (category, text, {String? noteId}) {
            if (noteId != null) {
              cubit.updateNote(noteId, text);
            }
            Navigator.pop(context);
          },
          onCancel: () => Navigator.pop(context),
        ),
      ),
    );
  }
```

- [ ] **Step 4: Update existing tests with mock providers**

Add mock classes and streams at the top of `annotation_editor_screen_test.dart`:

```dart
import 'package:horatio_app/bloc/recording/recording_cubit.dart';
import 'package:horatio_app/bloc/recording/recording_state.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';

class MockRecordingDao extends Mock implements RecordingDao {}
class MockRecordingService extends Mock implements RecordingService {}
class MockAudioPlaybackService extends Mock implements AudioPlaybackService {}
```

Add setup for recording mocks:

```dart
late MockRecordingDao _recordingDao;
late StreamController<List<LineRecording>> _recordingsCtrl;
late MockRecordingService _recordingService;
late MockAudioPlaybackService _playbackService;

void _setUpRecordingMocks() {
  _recordingDao = MockRecordingDao();
  _recordingsCtrl = StreamController<List<LineRecording>>.broadcast();
  _recordingService = MockRecordingService();
  _playbackService = MockAudioPlaybackService();

  when(() => _recordingDao.watchRecordingsForScript(any()))
      .thenAnswer((_) => _recordingsCtrl.stream);
}
```

Update `_setUpDao` to call `_setUpRecordingMocks()` at the end.
Update `_tearDownStreams` to also close `_recordingsCtrl`.

Update `_buildScreen` and `_buildScreenWithRouter` to provide the recording dependencies:

```dart
Widget _buildScreen(Script script) => MultiRepositoryProvider(
      providers: [
        RepositoryProvider<AnnotationDao>.value(value: _dao),
        RepositoryProvider<RecordingDao>.value(value: _recordingDao),
        RepositoryProvider<RecordingService>.value(value: _recordingService),
        RepositoryProvider<AudioPlaybackService>.value(
          value: _playbackService,
        ),
        RepositoryProvider<String>.value(value: '/tmp/test_recordings'),
      ],
      child: MaterialApp(
        home: AnnotationEditorScreen(script: script),
      ),
    );
```

Apply the same pattern to `_buildScreenWithRouter`.

- [ ] **Step 5: Add integration tests for the new interactions**

```dart
    testWidgets('shows recording action bar when line selected',
        (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _recordingsCtrl.add([]);
      await tester.pumpAndSettle();

      // Tap to select a line.
      await tester.tap(find.text('To be or not to be.'));
      await tester.pumpAndSettle();

      expect(find.byType(RecordingActionBar), findsOneWidget);
    });

    testWidgets('hides recording action bar when no line selected',
        (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _recordingsCtrl.add([]);
      await tester.pumpAndSettle();

      expect(find.byType(RecordingActionBar), findsNothing);
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
      await tester.pumpAndSettle();

      // Tap to select the first line.
      await tester.tap(find.text('To be or not to be.'));
      await tester.pumpAndSettle();

      expect(find.byType(NoteChip), findsOneWidget);
      expect(find.text('A test note'), findsOneWidget);
    });

    testWidgets('recording badge shows count for line', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _recordingsCtrl.add([
        LineRecording(
          id: 'r1',
          scriptId: 'editor-screen-test',
          lineIndex: 0,
          filePath: '/tmp/rec.m4a',
          durationMs: 5000,
          createdAt: DateTime.utc(2026),
        ),
      ]);
      await tester.pumpAndSettle();

      expect(find.byType(RecordingBadge), findsWidgets);
      expect(find.text('1'), findsOneWidget);
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

      when(() => _dao.deleteNote(any())).thenAnswer((_) async {});
      _marksCtrl.add([]);
      _notesCtrl.add([note]);
      _recordingsCtrl.add([]);
      await tester.pumpAndSettle();

      // Select line.
      await tester.tap(find.text('To be or not to be.'));
      await tester.pumpAndSettle();

      // Long-press the NoteChip.
      await tester.longPress(find.byType(NoteChip));
      await tester.pumpAndSettle();

      verify(() => _dao.deleteNote('n-del')).called(1);
    });
```

- [ ] **Step 7: Run all tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test
```

- [ ] **Step 8: Commit**

```bash
git add horatio_app/lib/screens/annotation_editor_screen.dart horatio_app/test/screens/annotation_editor_screen_test.dart
git commit -m "feat(screen): integrate recording UI, note chips, and recording badges"
```

---

### Task 6.3: Run full pipeline

- [ ] **Step 1: Run codegen + analyze + test**

```bash
cd /home/kuhy/testsAndMisc/horatio && ./run.sh test
```

Expected: 100% coverage, all analyses pass, dead code check clean.

- [ ] **Step 2: Fix any remaining issues**

Coverage gaps, lint warnings, dead code — fix iteratively until 100%.

---

### Task 6.4: Final commit

- [ ] **Step 1: Commit all remaining changes**

```bash
git add -A
git commit -m "feat: responsive font scaling, word-level marks, voice recording, note UX improvements"
```

- [ ] **Step 2: Confirm pipeline passes one final time**

```bash
cd /home/kuhy/testsAndMisc/horatio && ./run.sh -f test
```

Expected: All green.
