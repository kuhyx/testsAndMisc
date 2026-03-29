# Horatio — Annotations Subsystem Design Spec

## Overview

Add two layers of annotations to script lines:

1. **Text marks** — span-based delivery marks on words/syllables (stress, pause,
   breath, emphasis, tempo changes)
2. **Line notes** — free-text interpretive notes attached to a whole line (intention,
   subtext, blocking, emotion, delivery, general)

Both types include full change history via snapshots, enabling undo and annotation
evolution tracking over time.

## Approach

Drift-backed persistence (dependencies already in `pubspec.yaml`). This establishes
the SQLite persistence layer that Recording and future subsystems will reuse.

- Core models live in `horatio_core` (pure Dart, no Flutter dependency)
- Persistence, state management, and UI live in `horatio_app`
- Annotations bind to `ScriptLine` via `scriptId` (UUID) + `lineIndex`
- This spec also introduces a `scriptId` field on `Script` to provide a stable
  unique identifier for annotation binding (titles can collide)

## Data Models (horatio_core)

### MarkType Enum

```dart
enum MarkType {
  stress,    // Stress/emphasize this word
  pause,     // Pause before this span
  breath,    // Take a breath here
  emphasis,  // General emphasis
  slowDown,  // Deliver this span slower
  speedUp,   // Deliver this span faster
}
```

### NoteCategory Enum

```dart
enum NoteCategory {
  intention,  // "What does the character want here?"
  subtext,    // "What are they really saying?"
  blocking,   // "Cross downstage on this line"
  emotion,    // "Suppressed anger building"
  delivery,   // "Whisper this line"
  general,    // Catch-all
}
```

### TextMark

Span-based annotation on text within a line.

```dart
@immutable
final class TextMark {
  TextMark({
    required this.id,
    required this.lineIndex,
    required this.startOffset,
    required this.endOffset,
    required this.type,
    required this.createdAt,
  }) {
    assert(startOffset >= 0, 'startOffset must be non-negative');
    assert(endOffset > startOffset, 'endOffset must be greater than startOffset');
  }

  final String id;          // UUID
  final int lineIndex;      // Which ScriptLine
  final int startOffset;    // Start character offset in line text
  final int endOffset;      // End character offset (exclusive)
  final MarkType type;
  final DateTime createdAt;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is TextMark && id == other.id;

  @override
  int get hashCode => id.hashCode;

  Map<String, dynamic> toJson() => {
    'id': id,
    'lineIndex': lineIndex,
    'startOffset': startOffset,
    'endOffset': endOffset,
    'type': type.name,
    'createdAt': createdAt.toUtc().toIso8601String(),
  };

  factory TextMark.fromJson(Map<String, dynamic> json) => TextMark(
    id: json['id'] as String,
    lineIndex: json['lineIndex'] as int,
    startOffset: json['startOffset'] as int,
    endOffset: json['endOffset'] as int,
    type: MarkType.values.byName(json['type'] as String),
    createdAt: DateTime.parse(json['createdAt'] as String),
  );
}
```

### LineNote

Free-text note attached to a whole line.

```dart
@immutable
final class LineNote {
  const LineNote({
    required this.id,
    required this.lineIndex,
    required this.category,
    required this.text,
    required this.createdAt,
  });

  final String id;            // UUID
  final int lineIndex;        // Which ScriptLine
  final NoteCategory category;
  final String text;
  final DateTime createdAt;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is LineNote && id == other.id;

  @override
  int get hashCode => id.hashCode;

  Map<String, dynamic> toJson() => {
    'id': id,
    'lineIndex': lineIndex,
    'category': category.name,
    'text': text,
    'createdAt': createdAt.toUtc().toIso8601String(),
  };

  factory LineNote.fromJson(Map<String, dynamic> json) => LineNote(
    id: json['id'] as String,
    lineIndex: json['lineIndex'] as int,
    category: NoteCategory.values.byName(json['category'] as String),
    text: json['text'] as String,
    createdAt: DateTime.parse(json['createdAt'] as String),
  );
}
```

### AnnotationSnapshot

Point-in-time record of all annotations for a script. Enables change history,
undo/redo, and viewing annotation evolution over time.

```dart
@immutable
final class AnnotationSnapshot {
  AnnotationSnapshot({
    required this.id,
    required this.scriptId,
    required this.timestamp,
    required List<TextMark> marks,
    required List<LineNote> notes,
  }) : marks = List.unmodifiable(marks),
       notes = List.unmodifiable(notes);

  final String id;               // UUID
  final String scriptId;
  final DateTime timestamp;
  final List<TextMark> marks;    // Unmodifiable
  final List<LineNote> notes;    // Unmodifiable

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AnnotationSnapshot && id == other.id;

  @override
  int get hashCode => id.hashCode;

  Map<String, dynamic> toJson() => {
    'id': id,
    'scriptId': scriptId,
    'timestamp': timestamp.toUtc().toIso8601String(),
    'marks': marks.map((m) => m.toJson()).toList(),
    'notes': notes.map((n) => n.toJson()).toList(),
  };

  factory AnnotationSnapshot.fromJson(Map<String, dynamic> json) =>
      AnnotationSnapshot(
        id: json['id'] as String,
        scriptId: json['scriptId'] as String,
        timestamp: DateTime.parse(json['timestamp'] as String),
        marks: (json['marks'] as List<dynamic>)
            .map((e) => TextMark.fromJson(e as Map<String, dynamic>))
            .toList(),
        notes: (json['notes'] as List<dynamic>)
            .map((e) => LineNote.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
```

### Serialization

All `DateTime` values use UTC ISO 8601 format. Enums serialize by `name` (string).
Serialization is manual (no `json_serializable` dependency) to keep `horatio_core`
free of codegen. Invalid enum names in `fromJson` throw `ArgumentError` via
`EnumName.byName` — this is intentional; corrupted data should fail loudly.

## Persistence (Drift)

### Database Location

`horatio_app/lib/database/app_database.dart` — central drift database class.

This is the first use of drift in the app. Future subsystems (Recording, SRS
persistence) will add their tables to this same database.

### Tables

**text_marks:**

| Column      | Type     | Notes                   |
| ----------- | -------- | ----------------------- |
| id          | text PK  | UUID                    |
| scriptId    | text     | FK-like, UUID of script |
| lineIndex   | integer  |                         |
| startOffset | integer  |                         |
| endOffset   | integer  |                         |
| markType    | text     | Enum name string        |
| createdAt   | dateTime |                         |

**line_notes:**

| Column    | Type     | Notes                   |
| --------- | -------- | ----------------------- |
| id        | text PK  | UUID                    |
| scriptId  | text     | FK-like, UUID of script |
| lineIndex | integer  |                         |
| category  | text     | Enum name string        |
| noteText  | text     |                         |
| createdAt | dateTime |                         |

**annotation_snapshots:**

| Column       | Type     | Notes                         |
| ------------ | -------- | ----------------------------- |
| id           | text PK  | UUID                          |
| scriptId     | text     | UUID of script                |
| timestamp    | dateTime |                               |
| snapshotJson | text     | JSON-serialized marks + notes |

### DAO

`AnnotationDao` providing methods below. Note: `TextMark` and `LineNote` models
do not carry a `scriptId` field — the DAO binds `scriptId` at the persistence
boundary (on insert, and as a filter on queries). Models are always loaded in the
context of a known script.

Methods:

- `watchMarksForScript(scriptId)` → `Stream<List<TextMark>>`
- `watchNotesForScript(scriptId)` → `Stream<List<LineNote>>`
- `watchSnapshotsForScript(scriptId)` → `Stream<List<AnnotationSnapshot>>`
- `insertMark(scriptId, TextMark)`, `deleteMark(id)`
- `insertNote(scriptId, LineNote)`, `updateNoteText(id, text)`, `deleteNote(id)`
- `insertSnapshot(AnnotationSnapshot)` (snapshot carries its own `scriptId`)
- `getMarksForLine(scriptId, lineIndex)` → `Future<List<TextMark>>`
- `getNotesForLine(scriptId, lineIndex)` → `Future<List<LineNote>>`

## State Management

### AnnotationCubit

Handles annotation CRUD. Snapshot management is in a separate cubit (below).

```dart
sealed class AnnotationState extends Equatable {}

final class AnnotationInitial extends AnnotationState {}

final class AnnotationLoaded extends AnnotationState {
  final String scriptId;
  final List<TextMark> marks;
  final List<LineNote> notes;
  final int? selectedLineIndex;    // Currently focused line
  final EditingContext? editing;   // Non-null when actively editing
}

@immutable
final class EditingContext {
  const EditingContext({
    required this.lineIndex,
    required this.isAddingMark,
  });
  final int lineIndex;
  final bool isAddingMark;  // true = placing mark, false = writing note
}
```

**Methods:**

- `loadAnnotations(scriptId)` — subscribe to drift watch streams
- `selectLine(lineIndex)` — focus a line for annotation
- `startEditing(lineIndex, isAddingMark)` — enter editing mode
- `cancelEditing()` — exit editing mode
- `addMark(lineIndex, startOffset, endOffset, MarkType)` — create TextMark
- `removeMark(id)` — delete a mark
- `addNote(lineIndex, NoteCategory, text)` — create LineNote
- `updateNote(id, text)` — edit note content
- `removeNote(id)` — delete a note

### AnnotationHistoryCubit

Separate cubit for snapshot management (SRP: CRUD vs history are independent
concerns).

```dart
sealed class AnnotationHistoryState extends Equatable {}

final class AnnotationHistoryInitial extends AnnotationHistoryState {}

final class AnnotationHistoryLoaded extends AnnotationHistoryState {
  final String scriptId;
  final List<AnnotationSnapshot> snapshots;
}
```

**Methods:**

- `loadSnapshots(scriptId)` — subscribe to drift watch stream
- `saveSnapshot()` — capture current marks + notes as a snapshot
- `restoreSnapshot(snapshotId)` — delete all current annotations for the
  script and replace with snapshot contents. This is destructive; the UI
  must show a confirmation dialog before calling this.

## UI

### Annotation Editor Screen

Accessed from script detail (new route). Shows the full script text with:

- **Mark overlay:** Colored highlights on text spans. Each `MarkType` has a distinct
  color (e.g., stress = red underline, pause = blue caret, breath = green dot).
- **Note indicators:** Small icons next to lines that have notes. Tappable to
  expand/collapse.
- **Interaction:**
  - Tap-and-drag on text to select a span → choose mark type from popup
  - Tap a mark to remove it
  - Long-press a line → add/edit notes in a bottom sheet with category picker
- **Toolbar:** Mark type filter toggles, snapshot save button, history button

### Rehearsal Screen Enhancement

- During rehearsal, show text marks on the cue/expected lines as colored highlights
- Show note count badge next to lines that have notes
- Optional: tap badge to peek at notes without leaving rehearsal flow

### History View

- Timeline list of `AnnotationSnapshot` entries
- Each entry shows timestamp and diff summary (marks added/removed, notes changed)
- Tap to restore that snapshot (with confirmation)

## Testing Strategy

### horatio_core Tests

- `TextMark`: construction, equality, immutability, offset validation (assert
  failures for negative offsets, endOffset <= startOffset)
- `LineNote`: construction, equality, immutability
- `AnnotationSnapshot`: construction with unmodifiable lists, serialization
  roundtrip, empty marks/notes roundtrip, invalid enum names in JSON
  (expect `ArgumentError`), malformed DateTime strings (expect `FormatException`)
- `MarkType` / `NoteCategory`: all enum values covered in serialization
- `Script.id`: new field present, non-empty
- Target: 100% branch coverage

### horatio_app Tests

- **Drift DAO tests:** In-memory database, CRUD operations, reactive stream
  emissions, snapshot save/restore, restore-as-destructive-replace behavior
- **AnnotationCubit tests:** State transitions for load, select, start/cancel
  editing, add/remove marks and notes. Mock the DAO.
- **AnnotationHistoryCubit tests:** Load snapshots, save snapshot, restore
  snapshot (verify destructive replace). Mock the DAO.
- **Widget tests:** Annotation overlay renders marks correctly, tap interactions
  trigger cubit methods, note bottom sheet displays and submits, history timeline
  renders snapshots, restore confirmation dialog
- Target: 100% branch coverage

## File Structure

```
horatio_core/lib/src/models/
  text_mark.dart
  line_note.dart
  annotation_snapshot.dart
  mark_type.dart
  note_category.dart

horatio_app/lib/
  database/
    app_database.dart
    app_database.g.dart          (drift codegen)
    tables/
      text_marks_table.dart
      line_notes_table.dart
      annotation_snapshots_table.dart
    daos/
      annotation_dao.dart
      annotation_dao.g.dart      (drift codegen)
  bloc/annotation/
    annotation_cubit.dart
    annotation_state.dart
  screens/
    annotation_editor_screen.dart
    annotation_history_screen.dart
  widgets/
    mark_overlay.dart
    note_indicator.dart
    mark_type_picker.dart
    note_editor_sheet.dart
```

## Dependencies

**horatio_core** (new):

- `uuid` — for generating annotation IDs at model creation time

**horatio_app** (already present):

- `drift: ^2.22.0`
- `sqlite3_flutter_libs: ^0.6.0`
- `path_provider: ^2.1.0`
- `equatable: ^2.0.7`

**horatio_app** (new dev dependencies):

- `build_runner` — drift codegen runner
- `drift_dev` — drift code generator

**Build pipeline change:** Add `dart run build_runner build` step to `run.sh`
before the analyze/test steps (with caching so it only regenerates when
drift table definitions change).

## Migration Path

This is the first drift database in the app. Schema version starts at 1. Future
subsystems (Recording, SRS persistence) will add tables via drift schema migrations
(version 2, 3, etc.).

## Script Identity Change

This spec introduces a `scriptId` field (UUID) on the `Script` model in
`horatio_core`. Generated at parse time via `uuid` package. This provides a
stable unique identifier that annotations bind to.

```dart
final class Script {
  const Script({
    required this.id,
    required this.title,
    required this.roles,
    required this.scenes,
  });

  final String id;     // UUID, generated at parse time
  final String title;
  final List<Role> roles;
  final List<Scene> scenes;
  // ... existing methods unchanged
}
```

All existing code that creates `Script` instances (parsers, tests, demo data)
must be updated to supply an `id`.

## Open Decisions

- **Mark rendering:** Exact visual design (colors, underline styles, icons) will be
  finalized during implementation based on what looks readable.
- **Snapshot granularity:** Auto-snapshot on every edit vs manual-only. Starting with
  manual to keep it simple; auto-snapshot can be added later.
