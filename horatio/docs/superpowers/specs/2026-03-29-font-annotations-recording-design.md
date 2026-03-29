# Responsive Font, Working Annotations & Voice Recording — Design Spec

**Date**: 2026-03-29
**Status**: APPROVED (review round 2 passed — 17/17 original findings resolved, 3/3 new findings resolved)
**Scope**: Font scaling, word-level marks, note UX improvements, per-line voice recording with grading

---

## Problem Statement

Three issues identified by manual testing on a 4K Linux desktop:

1. **Font size**: Default Material 14sp body text renders unreadably small on high-DPI displays. No manual scaling control exists.
2. **Annotations partially broken**: Long-press marks the entire line (`startOffset: 0, endOffset: text.length`). Users cannot select specific words. Voice recording per line is unimplemented.
3. **Note UX**: Notes show only a count badge; there is no inline expansion, editing of existing notes, or deletion gesture.

## Out of Scope

- Demo mode (separate spec)
- SRS integration of voice recordings
- Cloud sync of recordings or annotations
- Multi-device recording format compatibility

---

## Section 1: Responsive Font Scaling

### Architecture

```
TextScaleCubit (flutter_bloc)
  ├── state: TextScaleState { scaleFactor: double }
  ├── loadScale()                          → reads SharedPreferences
  ├── setScale(double)                     → persists + emits
  └── autoDetect(Size size, double dpr)    → heuristic for 4K

SharedPreferences key: "text_scale_factor"
```

### Auto-Detection Heuristic

On first launch (no saved preference):

```
physicalWidth = size.width * devicePixelRatio

if physicalWidth >= 3200 (roughly 4K) AND platform is desktop:
    initialScale = 1.5
else:
    initialScale = 1.0
```

The heuristic only runs when no preference is saved. Once the user sets a manual value, it is always used.

**Context resolution**: `autoDetect` accepts raw `Size` and `double dpr` parameters (not a `BuildContext`) so it can be called before any `MediaQuery` override is applied. In `app.dart`, the auto-detection runs inside a `Builder` widget that sits **above** the `MediaQuery` text-scale override, reading the device's real `MediaQuery.of(context)` before it is wrapped.

### Manual Control

- **Settings icon** (gear) added to the app's main `AppBar` (home screen) and annotation editor `AppBar`
- Tapping opens a `BottomSheet` with:
  - `Slider` from 0.5 to 3.0, step 0.1
  - Live preview text: "Sample text at {scale}x"
  - "Reset to auto" button
- Value persisted immediately on slider change

### Integration Point

In `app.dart`, wrap `MaterialApp.router` in:

```dart
BlocBuilder<TextScaleCubit, TextScaleState>(
  builder: (context, state) => MediaQuery(
    data: MediaQuery.of(context).copyWith(
      textScaler: TextScaler.linear(state.scaleFactor),
    ),
    child: MaterialApp.router(...),
  ),
)
```

`TextScaleCubit` is provided in the `MultiBlocProvider` block in `app.dart` (alongside `ScriptImportCubit` and `SrsReviewCubit`), initialized with `loadScale()` in `main.dart`. Auto-detection is triggered from a `Builder` widget above the `MediaQuery` override.

### Files

| File                                                           | Action                                         |
| -------------------------------------------------------------- | ---------------------------------------------- |
| `horatio_app/lib/bloc/text_scale/text_scale_cubit.dart`        | NEW                                            |
| `horatio_app/lib/bloc/text_scale/text_scale_state.dart`        | NEW                                            |
| `horatio_app/lib/app.dart`                                     | MODIFY — wrap MaterialApp, add BlocProvider    |
| `horatio_app/lib/main.dart`                                    | MODIFY — init SharedPreferences, pass to cubit |
| `horatio_app/lib/widgets/text_scale_settings_sheet.dart`       | NEW                                            |
| `horatio_app/lib/screens/annotation_editor_screen.dart`        | MODIFY — add settings icon to AppBar           |
| `horatio_app/lib/screens/home_screen.dart`                     | MODIFY — add settings icon to AppBar           |
| `horatio_app/pubspec.yaml`                                     | MODIFY — add `shared_preferences`              |
| `horatio_app/test/bloc/text_scale_cubit_test.dart`             | NEW                                            |
| `horatio_app/test/widgets/text_scale_settings_sheet_test.dart` | NEW                                            |

---

## Section 2: Word-Level Mark Selection

### Interaction Flow

```
Tap line → line becomes "selected" (existing selectLine)
         → plain text switches to SelectableText.rich
         → user drags to select a word/phrase range

Selection change → floating MarkSelectionToolbar appears
                   above the selection with 6 colored chips

Tap chip → addMark(lineIndex, startOffset, endOffset, type)
         → toolbar dismisses, mark renders as colored span

Tap existing mark span → "Remove mark?" option
```

### Widget Changes

**`_LineTile` (in `annotation_editor_screen.dart`)**:

- When `isSelected == false`: render as current `MarkOverlay` (read-only `RichText`)
- When `isSelected == true`: render as `SelectableText.rich` with:
  - Same colored spans from marks
  - `onSelectionChanged` callback that captures `TextSelection`
  - `contextMenuBuilder` or `CompositedTransformFollower` for the toolbar

**`MarkSelectionToolbar` (new widget)**:

- Row of 6 `ActionChip` widgets, one per `MarkType`, colored with `markColors`
- Receives `onMarkSelected(MarkType)` callback
- Also includes "Cancel" button
- **Positioning**: Use `CompositedTransformTarget` on the `SelectableText` with a `LayerLink`. When selection changes, compute selection bounds via `RenderParagraph.getBoxesForSelection(selection)` to get the vertical offset, then show a `CompositedTransformFollower` with `OverlayEntry` anchored above the selection boxes. If the selection is near the top of the screen, position below instead.

**`AnnotationCubit` changes**:

- `addMark` already accepts `startOffset` / `endOffset` — no cubit changes needed
- `removeMark(markId)` already exists

### Selection-to-Offset Mapping

`SelectableText.rich` provides `TextSelection` with `baseOffset` and `extentOffset`. These map directly to character offsets in the line text, which match `TextMark.startOffset` / `endOffset`.

Edge case: if the user selects across an existing mark boundary, the new mark overlaps. This is fine — `MarkOverlay` already handles overlapping marks via boundary events.

### Files

| File                                                          | Action                              |
| ------------------------------------------------------------- | ----------------------------------- |
| `horatio_app/lib/widgets/mark_selection_toolbar.dart`         | NEW                                 |
| `horatio_app/lib/screens/annotation_editor_screen.dart`       | MODIFY — `_LineTile` selected state |
| `horatio_app/test/widgets/mark_selection_toolbar_test.dart`   | NEW                                 |
| `horatio_app/test/screens/annotation_editor_screen_test.dart` | MODIFY — word selection tests       |

---

## Section 3: Voice Recording Per Line

### New Model (horatio_core)

```dart
final class LineRecording {
  const LineRecording({
    required this.id,
    required this.scriptId,
    required this.lineIndex,
    required this.filePath,
    required this.durationMs,
    required this.createdAt,
    this.grade,
  });

  final String id;
  final String scriptId;
  final int lineIndex;
  final String filePath;
  final int durationMs;
  final DateTime createdAt;
  final int? grade; // 0-5, matches SM-2 quality scale
}
```

### Drift Table

```dart
class LineRecordingsTable extends Table {
  TextColumn get id => text()();
  TextColumn get scriptId => text()();
  IntColumn get lineIndex => integer()();
  TextColumn get filePath => text()();
  IntColumn get durationMs => integer()();
  DateTimeColumn get createdAt => dateTime()();
  IntColumn get grade => integer().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}
```

Added to `AppDatabase` tables list.

### Database Migration

Bump `schemaVersion` from 1 to 2. Add `MigrationStrategy` with:

```dart
@override
MigrationStrategy get migration => MigrationStrategy(
  onCreate: (m) => m.createAll(),
  onUpgrade: (m, from, to) async {
    if (from < 2) {
      await m.createTable(lineRecordingsTable);
    }
  },
);
```

### RecordingDao (new, separate from AnnotationDao)

A new `@DriftAccessor(tables: [LineRecordingsTable])` class with:

- `insertRecording(...)` / `deleteRecording(id)` / `updateRecordingGrade(id, grade)`
- `watchRecordingsForScript(scriptId)` → `Stream<List<LineRecording>>`

Keeping it separate from `AnnotationDao` maintains single-responsibility. Injected via its own `RepositoryProvider<RecordingDao>` in `app.dart`.

### Services

**`RecordingService`** (wraps `record` package):

- `Future<void> startRecording(String filePath)` — starts microphone capture to `.m4a`
- `Future<String> stopRecording()` — stops, returns file path
- `Stream<bool> get isRecording`
- `Stream<Duration> get amplitude` — periodic updates (~100ms) from the `record` package's amplitude stream, used by `RecordingCubit` to update `RecordingInProgress.elapsed` via a `Timer.periodic(Duration(milliseconds: 100))` that increments the elapsed counter
- `Future<bool> hasPermission()` / `Future<bool> requestPermission()`
- File naming: `recordings/{scriptId}/line_{lineIndex}_{timestamp}.m4a`
- Storage dir: `path_provider` `getApplicationDocumentsDirectory()`
- **Directory creation**: `startRecording` ensures the parent directory exists (`Directory.create(recursive: true)`) before starting capture
- **Linux note**: `hasPermission()` / `requestPermission()` are no-ops on desktop Linux (PulseAudio/PipeWire handles access). Tests mock both paths regardless.

**`AudioPlaybackService`** (new, wraps `audioplayers` package):

- `Future<void> play(String filePath)`
- `Future<void> stop()`
- `Stream<Duration> get position`
- `Stream<PlaybackStatus> get status` — enum: `idle`, `playing`, `completed`. `RecordingCubit` listens to this stream to transition from `RecordingPlayback` to `RecordingGrading` when status becomes `completed`.
- `Future<Duration> getDuration(String filePath)`

Both services are injected via `RepositoryProvider` in `app.dart`.

### RecordingCubit

```
States:
  RecordingInitial
  RecordingIdle(recordings: List<LineRecording>)
  RecordingInProgress(lineIndex: int, elapsed: Duration)
  RecordingPlayback(recording: LineRecording, position: Duration)
  RecordingGrading(recording: LineRecording)
  RecordingError(message: String)

Events/methods:
  loadRecordings(scriptId)
  startRecording(scriptId, lineIndex)
  stopRecording()
  playRecording(recordingId)
  stopPlayback()
  gradeRecording(recordingId, int grade)  // 0-5
  deleteRecording(recordingId)
```

`RecordingCubit` uses a `Timer.periodic(Duration(milliseconds: 100))` during recording to emit updated `RecordingInProgress` states with incrementing `elapsed`. The timer is cancelled on `stopRecording()` or `close()`.

For playback, the cubit subscribes to `AudioPlaybackService.status`. When status becomes `PlaybackStatus.completed`, it transitions to `RecordingGrading`. The `StreamSubscription` is cancelled on `stopPlayback()` and `close()` (same pattern as `AnnotationCubit`'s stream subscriptions).

Error handling: `playRecording` catches `FileNotFoundException`, calls `deleteRecording` on the DAO, and emits `RecordingError('Recording file not found')`. The UI shows a SnackBar via `BlocListener`.

### UI in Annotation Editor

When a line is selected, a **bottom action bar** appears below the line list:

```
┌─────────────────────────────────────────────┐
│  🎤 Record  │  ▶ Play (last)  │  ⭐ Grade  │
│  [hold or toggle]  │  [tap]   │  [0-5 stars]│
└─────────────────────────────────────────────┘
```

- **Mic button**: Tap to start, tap again to stop. Shows recording duration while active.
- **Play button**: Plays the most recent recording for the selected line. Disabled if no recordings.
- **Grade section**: After playback finishes, shows a `GradeStars` widget. Displays 5 tappable star icons (1-5) plus a dedicated "0" button labeled "Blackout" for grade 0 (complete failure in SM-2). The `null` grade (not-yet-graded) is visually distinct: all stars are outlined/empty with no "0" highlight. Grade saves to DB immediately on tap.
- **Recording badge**: Next to `NoteIndicator`, a small mic icon with count shows recordings per line.

**Recording list**: Tap the recording badge to see all recordings for that line in a bottom sheet. Each item shows: duration, date, grade stars. Swipe to delete.

### Dependencies

| Package              | Version            | Purpose                |
| -------------------- | ------------------ | ---------------------- |
| `record`             | already in pubspec | Microphone recording   |
| `audioplayers`       | ^6.1.0             | Audio playback         |
| `shared_preferences` | ^2.3.0             | Font scale persistence |

### Files

| File                                                         | Action                                            |
| ------------------------------------------------------------ | ------------------------------------------------- |
| `horatio_core/lib/src/models/line_recording.dart`            | NEW                                               |
| `horatio_core/lib/src/models/models.dart`                    | MODIFY — barrel export                            |
| `horatio_app/lib/database/tables/line_recordings_table.dart` | NEW                                               |
| `horatio_app/lib/database/app_database.dart`                 | MODIFY — add table, bump schema, add migration    |
| `horatio_app/lib/database/daos/recording_dao.dart`           | NEW — recording CRUD                              |
| `horatio_app/lib/services/recording_service.dart`            | NEW                                               |
| `horatio_app/lib/services/audio_playback_service.dart`       | NEW                                               |
| `horatio_app/lib/bloc/recording/recording_cubit.dart`        | NEW                                               |
| `horatio_app/lib/bloc/recording/recording_state.dart`        | NEW                                               |
| `horatio_app/lib/widgets/recording_badge.dart`               | NEW                                               |
| `horatio_app/lib/widgets/recording_action_bar.dart`          | NEW                                               |
| `horatio_app/lib/widgets/recording_list_sheet.dart`          | NEW                                               |
| `horatio_app/lib/widgets/grade_stars.dart`                   | NEW                                               |
| `horatio_app/lib/screens/annotation_editor_screen.dart`      | MODIFY — integrate recording UI                   |
| `horatio_app/lib/app.dart`                                   | MODIFY — provide RecordingDao + services          |
| `horatio_app/pubspec.yaml`                                   | MODIFY — add `audioplayers`, `shared_preferences` |
| `horatio_app/test/database/recording_dao_test.dart`          | NEW                                               |
| `horatio_app/test/services/recording_service_test.dart`      | NEW                                               |
| `horatio_app/test/services/audio_playback_service_test.dart` | NEW                                               |
| `horatio_app/test/bloc/recording_cubit_test.dart`            | NEW                                               |
| `horatio_app/test/widgets/recording_badge_test.dart`         | NEW                                               |
| `horatio_app/test/widgets/recording_action_bar_test.dart`    | NEW                                               |
| `horatio_app/test/widgets/recording_list_sheet_test.dart`    | NEW                                               |
| `horatio_app/test/widgets/grade_stars_test.dart`             | NEW                                               |

---

## Section 4: Note UX Improvements

### Inline Note Expansion

When a line is selected and has notes:

- Notes render as expandable `Chip` widgets below the line text (inside `_LineTile`)
- Each chip shows: category icon + truncated text (max 30 chars)
- Tap chip → `NoteEditorSheet` pre-filled with existing text + category (for editing)
- Long-press or swipe chip → delete confirmation

### Note Editing

`NoteEditorSheet` already supports `initialText` and `initialCategory`. The edit flow:

1. Tap existing note chip
2. Sheet opens with pre-filled values
3. Save calls `cubit.updateNote(noteId, newCategory, newText)` instead of `addNote`

**Signature changes required**:

- `AnnotationDao`: add `updateNoteCategory(String id, NoteCategory category)` method
- `AnnotationCubit`: change `updateNote` to accept `(String id, {String? text, NoteCategory? category})` and call the appropriate DAO methods
- `NoteEditorSheet`: add optional `noteId` parameter. When `noteId` is non-null, `onSave` includes it in the callback so the caller can distinguish create vs update. Callback type becomes `void Function(NoteCategory, String, {String? noteId})`.

### Files

| File                                                          | Action                                 |
| ------------------------------------------------------------- | -------------------------------------- |
| `horatio_app/lib/screens/annotation_editor_screen.dart`       | MODIFY — note chips in `_LineTile`     |
| `horatio_app/lib/widgets/note_chip.dart`                      | NEW — tappable note chip widget        |
| `horatio_app/lib/widgets/note_editor_sheet.dart`              | MODIFY — add `noteId` parameter        |
| `horatio_app/lib/bloc/annotation/annotation_cubit.dart`       | MODIFY — `updateNote` accepts category |
| `horatio_app/lib/database/daos/annotation_dao.dart`           | MODIFY — add `updateNoteCategory`      |
| `horatio_app/test/widgets/note_chip_test.dart`                | NEW                                    |
| `horatio_app/test/screens/annotation_editor_screen_test.dart` | MODIFY — note editing tests            |

---

## Section 5: Error Handling

| Scenario                             | Handling                                                      | Actor                                                                                                                   |
| ------------------------------------ | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Microphone permission denied         | SnackBar: "Microphone permission required for recording"      | `RecordingCubit` emits `RecordingError`, UI shows via `BlocListener`                                                    |
| Recording fails (no mic, disk full)  | SnackBar with error message, state returns to `RecordingIdle` | `RecordingCubit` catches, emits `RecordingError` then `RecordingIdle`                                                   |
| Audio file not found on playback     | SnackBar: "Recording file not found", remove from DB          | `RecordingCubit.playRecording` catches `FileNotFoundException`, calls `dao.deleteRecording(id)`, emits `RecordingError` |
| SharedPreferences unavailable        | Fall back to default scale 1.0, no persistence                | `TextScaleCubit.loadScale` catches, uses default                                                                        |
| Text selection empty (0-length)      | Don't show toolbar, ignore                                    | `_LineTile.onSelectionChanged` checks `selection.isCollapsed`                                                           |
| Already recording when start pressed | Ignore (button disabled while `RecordingInProgress`)          | UI disables mic button via state check                                                                                  |

---

## Section 6: Testing Strategy

### General

- **100% branch coverage** maintained, `.g.dart` and table files filtered in `run.sh`
- `SharedPreferences.setMockInitialValues({})` required in `setUp` for all `TextScaleCubit` tests
- All `RecordingService` and `AudioPlaybackService` interactions mocked — no real mic or audio

### Branch Coverage Matrix

**TextScaleCubit**:

- `loadScale`: (a) no saved value → default 1.0, (b) saved value → load it
- `autoDetect`: (a) 4K desktop → 1.5, (b) non-4K → 1.0, (c) mobile platform → 1.0, (d) already has saved pref → skip
- `setScale`: persist + emit, slider interaction widget test

**RecordingCubit**:

- `startRecording`: (a) success → `RecordingInProgress`, (b) permission denied → `RecordingError`, (c) already recording → ignored
- `stopRecording`: success → `RecordingIdle` with new recording in list
- `playRecording`: (a) success → `RecordingPlayback`, (b) file not found → `RecordingError` + DB delete
- `stopPlayback`: → `RecordingIdle`
- Playback completion: `PlaybackStatus.completed` → `RecordingGrading`
- `gradeRecording`: (a) grade 0 → save, (b) grade 5 → save, (c) null (not yet graded)
- `deleteRecording`: removes from list + DB
- `Timer.periodic` cancel on `close()`

**MarkSelectionToolbar**: Chip tap callbacks, cancel button, positioning above/below

**Word selection**: Widget test with simulated `TextSelection` on `SelectableText.rich`, verify `addMark` called with correct start/end offsets. Test collapsed selection → no toolbar.

**RecordingDao**: CRUD integration tests (insert, delete, update grade, watch stream)

**Note chips**: Tap → edit (pre-filled sheet), long-press → delete confirmation, rendering with truncation, category icon display

**NoteEditorSheet**: Create mode (no noteId) vs edit mode (with noteId), category change vs text-only change

**GradeStars**: Tap star 1-5, tap "Blackout" (grade 0), display for null grade vs graded

---

## Data Flow Diagram

```
User taps line
  → AnnotationCubit.selectLine(index)
  → _LineTile re-renders as SelectableText.rich

User drags text selection
  → onSelectionChanged(TextSelection)
  → MarkSelectionToolbar appears with 6 chips

User taps chip
  → AnnotationCubit.addMark(line, start, end, type)
  → Drift insert → stream update → UI re-renders with colored span

User taps mic
  → RecordingCubit.startRecording(scriptId, lineIndex)
  → RecordingService.startRecording(filePath)
  → UI shows elapsed timer

User taps mic again
  → RecordingCubit.stopRecording()
  → RecordingService.stopRecording() → file on disk
  → Drift insert → stream update → recording badge count updates

User taps play
  → RecordingCubit.playRecording(id)
  → AudioPlaybackService.play(filePath)
  → Position stream updates progress bar

Playback finishes
  → RecordingGrading state
  → GradeStars widget visible
  → User taps star → RecordingCubit.gradeRecording(id, grade)
  → Drift update

User adjusts font slider
  → TextScaleCubit.setScale(value)
  → SharedPreferences persist
  → MediaQuery textScaler override → entire app re-renders
```
