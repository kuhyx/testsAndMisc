# Annotations Subsystem Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development
> (if subagents available) or superpowers:executing-plans to implement this plan.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add text-level marks and line-level notes to script lines with drift
persistence and change history via snapshots.

**Architecture:** Core annotation models (TextMark, LineNote, AnnotationSnapshot)
in `horatio_core`. Drift database, DAOs, cubits, and UI screens in `horatio_app`.
Two cubits: `AnnotationCubit` for CRUD, `AnnotationHistoryCubit` for snapshots.

**Tech Stack:** Dart 3.11, Flutter 3.x, drift 2.22, flutter_bloc 9, equatable 2,
uuid, build_runner + drift_dev (codegen)

**Spec:** `docs/superpowers/specs/2026-03-29-annotations-design.md`

---

## Chunk 1: Core Models + Script Identity

### Task 1: Add `uuid` and `meta` dependencies to horatio_core

**Files:**

- Modify: `horatio_core/pubspec.yaml:11-14`

- [ ] **Step 1: Add uuid and meta dependencies**

Add `uuid` and `meta` to the dependencies section of `horatio_core/pubspec.yaml`.
`meta` is needed for `@immutable` on `TextMark` and `AnnotationSnapshot`:

```yaml
dependencies:
  collection: ^1.18.0
  meta: ^1.16.0
  uuid: ^4.5.1
  xml: ^6.5.0
  archive: ^4.0.0
```

- [ ] **Step 2: Run pub get to verify**

```bash
cd horatio_core && dart pub get
```

Expected: resolves successfully, no errors.

- [ ] **Step 3: Commit**

```bash
git add horatio_core/pubspec.yaml horatio_core/pubspec.lock
git commit -m "feat(core): add uuid and meta dependencies for annotations"
```

---

### Task 2: Add `id` field to Script model

**Files:**

- Modify: `horatio_core/lib/src/models/script.dart`
- Modify: `horatio_core/test/models/model_test.dart`

- [ ] **Step 1: Write failing test for Script.id**

Add to `horatio_core/test/models/model_test.dart` in the `Script` group:

```dart
    test('id field is accessible', () {
      const script = Script(
        id: 'test-uuid-123',
        title: 'Test',
        roles: [],
        scenes: [],
      );
      expect(script.id, 'test-uuid-123');
    });

    // NOTE: 'toString includes title, role count, scene count' test already
    // exists in model_test.dart. Update testScript to include `id:` parameter
    // instead of adding a duplicate test.
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd horatio_core && dart test test/models/model_test.dart -v
```

Expected: compilation error — `Script` doesn't have an `id` parameter.

- [ ] **Step 3: Add id field to Script**

Modify `horatio_core/lib/src/models/script.dart`:

```dart
import 'package:horatio_core/src/models/role.dart';
import 'package:horatio_core/src/models/scene.dart';

/// A fully parsed script with metadata, roles, and scenes.
final class Script {
  /// Creates a [Script] from parsed data.
  const Script({
    required this.id,
    required this.title,
    required this.roles,
    required this.scenes,
  });

  /// Unique identifier (UUID) for this script.
  final String id;

  /// The title of the script.
  final String title;

  /// All character roles detected in the script.
  final List<Role> roles;

  /// Scenes in order.
  final List<Scene> scenes;

  /// Returns all lines in the script across all scenes.
  int get totalLineCount =>
      scenes.fold(0, (sum, scene) => sum + scene.lines.length);

  /// Returns the number of lines for a specific [role].
  int lineCountForRole(Role role) => scenes.fold(
    0,
    (sum, scene) => sum + scene.lines.where((line) => line.role == role).length,
  );

  @override
  String toString() =>
      'Script($title, ${roles.length} roles, ${scenes.length} scenes)';
}
```

- [ ] **Step 4: Fix all callers that create Script instances**

Every `Script(...)` constructor call now needs an `id:` parameter. Update these
files (find all sites with `grep -rn 'Script(' horatio/`):

1. `horatio_core/test/models/model_test.dart` — add `id: 'test-id'` to all
   `Script(...)` calls
2. `horatio_core/lib/src/parser/text_parser.dart` — add UUID import and
   generate ID at parse time. Add to the top of the file:
   ```dart
   import 'package:uuid/uuid.dart';
   ```
   Replace the existing `return Script(...)` in the `parse()` method with:
   ```dart
   return Script(
     id: const Uuid().v4(),
     title: title,
     roles: List.unmodifiable(roles.values.toList()),
     scenes: List.unmodifiable(scenes),
   );
   ```
3. `horatio_core/test/parser/text_parser_test.dart` — update any hardcoded
   Script assertions to allow any `id`
4. `horatio_core/test/planner/planner_test.dart` — add `id:` to test scripts
5. `horatio_core/test/srs/srs_test.dart` — add `id:` if Script is constructed
6. `horatio_app/test/` — add `id:` to ALL test files that create Script objects.
   Search for `Script(` across the test directory.
7. `horatio_app/lib/bloc/script_import/script_import_cubit.dart` — ensure
   parser-created scripts already have IDs (parser generates them)
8. Asset-loaded scripts (`importFromAsset`) — parse via TextParser which
   generates UUID, so no change needed
9. Any demo/fixture scripts in test helpers

Run a workspace-wide search for `Script(` to find every site.

- [ ] **Step 5: Run all tests to verify**

```bash
cd horatio_core && dart test
cd ../horatio_app && flutter test
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(core): add id (UUID) field to Script model"
```

---

### Task 3: Add MarkType and NoteCategory enums

**Files:**

- Create: `horatio_core/lib/src/models/mark_type.dart`
- Create: `horatio_core/lib/src/models/note_category.dart`
- Modify: `horatio_core/lib/src/models/models.dart` (barrel exports)

- [ ] **Step 1: Create MarkType enum**

Create `horatio_core/lib/src/models/mark_type.dart`:

```dart
/// Types of text-level delivery marks an actor can place on script text.
enum MarkType {
  /// Stress / emphasize this word.
  stress,

  /// Pause before this span.
  pause,

  /// Take a breath here.
  breath,

  /// General emphasis.
  emphasis,

  /// Deliver this span slower.
  slowDown,

  /// Deliver this span faster.
  speedUp,
}
```

- [ ] **Step 2: Create NoteCategory enum**

Create `horatio_core/lib/src/models/note_category.dart`:

```dart
/// Categories for line-level interpretive notes.
enum NoteCategory {
  /// "What does the character want here?"
  intention,

  /// "What are they really saying?"
  subtext,

  /// "Cross downstage on this line."
  blocking,

  /// "Suppressed anger building."
  emotion,

  /// "Whisper this line."
  delivery,

  /// Catch-all for uncategorized notes.
  general,
}
```

- [ ] **Step 3: Add barrel exports**

Add to `horatio_core/lib/src/models/models.dart`:

```dart
export 'mark_type.dart';
export 'note_category.dart';
export 'role.dart';
export 'scene.dart';
export 'script.dart';
export 'script_line.dart';
export 'srs_card.dart';
export 'stage_direction.dart';
```

- [ ] **Step 4: Run analysis**

```bash
cd horatio_core && dart analyze --fatal-infos
```

Expected: no issues.

> **Note (S1):** Enum value count tests (`expect(MarkType.values.length, 6)`)
> are not needed separately — the serialization round-trip tests in Tasks 4
> and 5 iterate all enum values, catching any accidental additions or removals.

- [ ] **Step 5: Commit**

```bash
git add horatio_core/lib/src/models/mark_type.dart \
        horatio_core/lib/src/models/note_category.dart \
        horatio_core/lib/src/models/models.dart
git commit -m "feat(core): add MarkType and NoteCategory enums"
```

---

### Task 4: Add TextMark model

**Files:**

- Create: `horatio_core/lib/src/models/text_mark.dart`
- Modify: `horatio_core/lib/src/models/models.dart`
- Modify: `horatio_core/test/models/model_test.dart`

- [ ] **Step 1: Write failing tests**

Add to `horatio_core/test/models/model_test.dart`:

```dart
  group('TextMark', () {
    test('construction with valid offsets', () {
      final mark = TextMark(
        id: 'mark-1',
        lineIndex: 0,
        startOffset: 5,
        endOffset: 10,
        type: MarkType.stress,
        createdAt: DateTime.utc(2026, 3, 29),
      );
      expect(mark.id, 'mark-1');
      expect(mark.lineIndex, 0);
      expect(mark.startOffset, 5);
      expect(mark.endOffset, 10);
      expect(mark.type, MarkType.stress);
    });

    test('equality uses id only', () {
      final a = TextMark(
        id: 'mark-1',
        lineIndex: 0,
        startOffset: 5,
        endOffset: 10,
        type: MarkType.stress,
        createdAt: DateTime.utc(2026, 3, 29),
      );
      final b = TextMark(
        id: 'mark-1',
        lineIndex: 99,
        startOffset: 0,
        endOffset: 1,
        type: MarkType.pause,
        createdAt: DateTime.utc(2026, 1, 1),
      );
      final c = TextMark(
        id: 'mark-2',
        lineIndex: 0,
        startOffset: 5,
        endOffset: 10,
        type: MarkType.stress,
        createdAt: DateTime.utc(2026, 3, 29),
      );
      expect(a, equals(b));
      expect(a, isNot(equals(c)));
      expect(a == a, isTrue); // identical
    });

    test('hashCode consistent with equality', () {
      final a = TextMark(
        id: 'mark-1',
        lineIndex: 0,
        startOffset: 5,
        endOffset: 10,
        type: MarkType.stress,
        createdAt: DateTime.utc(2026, 3, 29),
      );
      final b = TextMark(
        id: 'mark-1',
        lineIndex: 99,
        startOffset: 0,
        endOffset: 1,
        type: MarkType.pause,
        createdAt: DateTime.utc(2026, 1, 1),
      );
      expect(a.hashCode, b.hashCode);
    });

    test('assert fails for negative startOffset', () {
      expect(
        () => TextMark(
          id: 'x',
          lineIndex: 0,
          startOffset: -1,
          endOffset: 5,
          type: MarkType.stress,
          createdAt: DateTime.utc(2026),
        ),
        throwsA(isA<AssertionError>()),
      );
    });

    test('assert fails when endOffset <= startOffset', () {
      expect(
        () => TextMark(
          id: 'x',
          lineIndex: 0,
          startOffset: 5,
          endOffset: 5,
          type: MarkType.stress,
          createdAt: DateTime.utc(2026),
        ),
        throwsA(isA<AssertionError>()),
      );
    });

    test('toJson roundtrip', () {
      final original = TextMark(
        id: 'mark-1',
        lineIndex: 3,
        startOffset: 0,
        endOffset: 7,
        type: MarkType.breath,
        createdAt: DateTime.utc(2026, 3, 29, 12, 30),
      );
      final json = original.toJson();
      final restored = TextMark.fromJson(json);
      expect(restored.id, original.id);
      expect(restored.lineIndex, original.lineIndex);
      expect(restored.startOffset, original.startOffset);
      expect(restored.endOffset, original.endOffset);
      expect(restored.type, original.type);
      expect(restored.createdAt, original.createdAt);
    });

    test('fromJson with invalid type throws ArgumentError', () {
      final json = {
        'id': 'x',
        'lineIndex': 0,
        'startOffset': 0,
        'endOffset': 1,
        'type': 'nonexistent',
        'createdAt': '2026-03-29T00:00:00.000Z',
      };
      expect(() => TextMark.fromJson(json), throwsArgumentError);
    });

    test('toJson serializes all MarkType values', () {
      for (final type in MarkType.values) {
        final mark = TextMark(
          id: 'id-${type.name}',
          lineIndex: 0,
          startOffset: 0,
          endOffset: 1,
          type: type,
          createdAt: DateTime.utc(2026),
        );
        final json = mark.toJson();
        expect(json['type'], type.name);
        final restored = TextMark.fromJson(json);
        expect(restored.type, type);
      }
    });
  });
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd horatio_core && dart test test/models/model_test.dart -v
```

Expected: compilation error — `TextMark` not defined.

- [ ] **Step 3: Create TextMark model**

Create `horatio_core/lib/src/models/text_mark.dart`:

```dart
import 'package:meta/meta.dart';

import 'package:horatio_core/src/models/mark_type.dart';

/// A span-based delivery mark on text within a script line.
@immutable
final class TextMark {
  /// Creates a [TextMark] with validated offsets.
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

  /// Unique identifier (UUID).
  final String id;

  /// Index of the [ScriptLine] this mark applies to.
  final int lineIndex;

  /// Start character offset in the line text (inclusive).
  final int startOffset;

  /// End character offset in the line text (exclusive).
  final int endOffset;

  /// The type of delivery mark.
  final MarkType type;

  /// When this mark was created.
  final DateTime createdAt;

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is TextMark && id == other.id;

  @override
  int get hashCode => id.hashCode;

  /// Serializes to a JSON-compatible map.
  Map<String, dynamic> toJson() => {
    'id': id,
    'lineIndex': lineIndex,
    'startOffset': startOffset,
    'endOffset': endOffset,
    'type': type.name,
    'createdAt': createdAt.toUtc().toIso8601String(),
  };

  /// Deserializes from a JSON map.
  ///
  /// Throws [ArgumentError] if [type] is not a valid [MarkType] name.
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

- [ ] **Step 4: Add export to models.dart**

Add `export 'text_mark.dart';` to `horatio_core/lib/src/models/models.dart`.

- [ ] **Step 5: Run tests**

```bash
cd horatio_core && dart test test/models/model_test.dart -v
```

Expected: all TextMark tests pass.

- [ ] **Step 6: Commit**

```bash
git add horatio_core/lib/src/models/text_mark.dart \
        horatio_core/lib/src/models/models.dart \
        horatio_core/test/models/model_test.dart
git commit -m "feat(core): add TextMark model with serialization"
```

---

### Task 5: Add LineNote model

**Files:**

- Create: `horatio_core/lib/src/models/line_note.dart`
- Modify: `horatio_core/lib/src/models/models.dart`
- Modify: `horatio_core/test/models/model_test.dart`

- [ ] **Step 1: Write failing tests**

Add to `horatio_core/test/models/model_test.dart`:

```dart
  group('LineNote', () {
    test('construction fields accessible', () {
      final note = LineNote(
        id: 'note-1',
        lineIndex: 5,
        category: NoteCategory.intention,
        text: 'Character hiding anger',
        createdAt: DateTime.utc(2026, 3, 29),
      );
      expect(note.id, 'note-1');
      expect(note.lineIndex, 5);
      expect(note.category, NoteCategory.intention);
      expect(note.text, 'Character hiding anger');
      expect(note.createdAt, DateTime.utc(2026, 3, 29));
    });

    test('equality uses id only', () {
      final a = LineNote(
        id: 'note-1',
        lineIndex: 0,
        category: NoteCategory.intention,
        text: 'text a',
        createdAt: DateTime.utc(2026),
      );
      final b = LineNote(
        id: 'note-1',
        lineIndex: 99,
        category: NoteCategory.blocking,
        text: 'text b',
        createdAt: DateTime.utc(2020),
      );
      final c = LineNote(
        id: 'note-2',
        lineIndex: 0,
        category: NoteCategory.intention,
        text: 'text a',
        createdAt: DateTime.utc(2026),
      );
      expect(a, equals(b));
      expect(a, isNot(equals(c)));
      expect(a == a, isTrue); // identical
    });

    test('hashCode consistent with equality', () {
      final a = LineNote(
        id: 'note-1',
        lineIndex: 0,
        category: NoteCategory.intention,
        text: 'x',
        createdAt: DateTime.utc(2026),
      );
      final b = LineNote(
        id: 'note-1',
        lineIndex: 99,
        category: NoteCategory.subtext,
        text: 'y',
        createdAt: DateTime.utc(2020),
      );
      expect(a.hashCode, b.hashCode);
    });

    test('toJson roundtrip', () {
      final original = LineNote(
        id: 'note-1',
        lineIndex: 3,
        category: NoteCategory.subtext,
        text: 'Hidden meaning here',
        createdAt: DateTime.utc(2026, 3, 29, 14),
      );
      final json = original.toJson();
      final restored = LineNote.fromJson(json);
      expect(restored.id, original.id);
      expect(restored.lineIndex, original.lineIndex);
      expect(restored.category, original.category);
      expect(restored.text, original.text);
      expect(restored.createdAt, original.createdAt);
    });

    test('fromJson with invalid category throws ArgumentError', () {
      final json = {
        'id': 'x',
        'lineIndex': 0,
        'category': 'nonexistent',
        'text': 'note',
        'createdAt': '2026-03-29T00:00:00.000Z',
      };
      expect(() => LineNote.fromJson(json), throwsArgumentError);
    });

    test('toJson serializes all NoteCategory values', () {
      for (final cat in NoteCategory.values) {
        final note = LineNote(
          id: 'id-${cat.name}',
          lineIndex: 0,
          category: cat,
          text: 'test',
          createdAt: DateTime.utc(2026),
        );
        final json = note.toJson();
        expect(json['category'], cat.name);
        final restored = LineNote.fromJson(json);
        expect(restored.category, cat);
      }
    });
  });
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd horatio_core && dart test test/models/model_test.dart -v
```

- [ ] **Step 3: Create LineNote model**

Create `horatio_core/lib/src/models/line_note.dart`:

```dart
import 'package:meta/meta.dart';

import 'package:horatio_core/src/models/note_category.dart';

/// A free-text interpretive note attached to a whole script line.
@immutable
final class LineNote {
  /// Creates a [LineNote].
  const LineNote({
    required this.id,
    required this.lineIndex,
    required this.category,
    required this.text,
    required this.createdAt,
  });

  /// Unique identifier (UUID).
  final String id;

  /// Index of the [ScriptLine] this note is attached to.
  final int lineIndex;

  /// The category of this note.
  final NoteCategory category;

  /// Free-text note content.
  final String text;

  /// When this note was created.
  final DateTime createdAt;

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is LineNote && id == other.id;

  @override
  int get hashCode => id.hashCode;

  /// Serializes to a JSON-compatible map.
  Map<String, dynamic> toJson() => {
    'id': id,
    'lineIndex': lineIndex,
    'category': category.name,
    'text': text,
    'createdAt': createdAt.toUtc().toIso8601String(),
  };

  /// Deserializes from a JSON map.
  ///
  /// Throws [ArgumentError] if [category] is not a valid [NoteCategory] name.
  factory LineNote.fromJson(Map<String, dynamic> json) => LineNote(
    id: json['id'] as String,
    lineIndex: json['lineIndex'] as int,
    category: NoteCategory.values.byName(json['category'] as String),
    text: json['text'] as String,
    createdAt: DateTime.parse(json['createdAt'] as String),
  );
}
```

- [ ] **Step 4: Add export and run tests**

Add `export 'line_note.dart';` to `models.dart`, then:

```bash
cd horatio_core && dart test test/models/model_test.dart -v
```

Expected: all LineNote tests pass.

- [ ] **Step 5: Commit**

```bash
git add horatio_core/lib/src/models/line_note.dart \
        horatio_core/lib/src/models/models.dart \
        horatio_core/test/models/model_test.dart
git commit -m "feat(core): add LineNote model with serialization"
```

---

### Task 6: Add AnnotationSnapshot model

**Files:**

- Create: `horatio_core/lib/src/models/annotation_snapshot.dart`
- Modify: `horatio_core/lib/src/models/models.dart`
- Modify: `horatio_core/test/models/model_test.dart`

- [ ] **Step 1: Write failing tests**

Add to `horatio_core/test/models/model_test.dart`:

```dart
  group('AnnotationSnapshot', () {
    test('construction with unmodifiable lists', () {
      final marks = [
        TextMark(
          id: 'm1',
          lineIndex: 0,
          startOffset: 0,
          endOffset: 5,
          type: MarkType.stress,
          createdAt: DateTime.utc(2026),
        ),
      ];
      final notes = [
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'test',
          createdAt: DateTime.utc(2026),
        ),
      ];
      final snapshot = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'script-uuid',
        timestamp: DateTime.utc(2026, 3, 29),
        marks: marks,
        notes: notes,
      );
      expect(snapshot.marks.length, 1);
      expect(snapshot.notes.length, 1);
      // Lists should be unmodifiable.
      expect(() => snapshot.marks.add(marks.first), throwsUnsupportedError);
      expect(() => snapshot.notes.add(notes.first), throwsUnsupportedError);
    });

    test('equality uses id only', () {
      final a = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'script-a',
        timestamp: DateTime.utc(2026),
        marks: [],
        notes: [],
      );
      final b = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'script-b',
        timestamp: DateTime.utc(2020),
        marks: [],
        notes: [],
      );
      final c = AnnotationSnapshot(
        id: 'snap-2',
        scriptId: 'script-a',
        timestamp: DateTime.utc(2026),
        marks: [],
        notes: [],
      );
      expect(a, equals(b));
      expect(a, isNot(equals(c)));
      expect(a == a, isTrue);
    });

    test('hashCode consistent with equality', () {
      final a = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'script-a',
        timestamp: DateTime.utc(2026),
        marks: [],
        notes: [],
      );
      final b = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'script-b',
        timestamp: DateTime.utc(2020),
        marks: [],
        notes: [],
      );
      expect(a.hashCode, b.hashCode);
    });

    test('toJson roundtrip with empty lists', () {
      final original = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'script-uuid',
        timestamp: DateTime.utc(2026, 3, 29),
        marks: [],
        notes: [],
      );
      final json = original.toJson();
      final restored = AnnotationSnapshot.fromJson(json);
      expect(restored.id, original.id);
      expect(restored.scriptId, original.scriptId);
      expect(restored.timestamp, original.timestamp);
      expect(restored.marks, isEmpty);
      expect(restored.notes, isEmpty);
    });

    test('toJson roundtrip with populated lists', () {
      final mark = TextMark(
        id: 'm1',
        lineIndex: 0,
        startOffset: 0,
        endOffset: 5,
        type: MarkType.emphasis,
        createdAt: DateTime.utc(2026, 3, 29, 10),
      );
      final note = LineNote(
        id: 'n1',
        lineIndex: 0,
        category: NoteCategory.emotion,
        text: 'angry',
        createdAt: DateTime.utc(2026, 3, 29, 11),
      );
      final original = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'script-uuid',
        timestamp: DateTime.utc(2026, 3, 29, 12),
        marks: [mark],
        notes: [note],
      );
      final json = original.toJson();
      final restored = AnnotationSnapshot.fromJson(json);
      expect(restored.marks.length, 1);
      expect(restored.marks.first.id, 'm1');
      expect(restored.marks.first.type, MarkType.emphasis);
      expect(restored.notes.length, 1);
      expect(restored.notes.first.id, 'n1');
      expect(restored.notes.first.category, NoteCategory.emotion);
    });

    test('fromJson with malformed DateTime throws FormatException', () {
      final json = {
        'id': 'x',
        'scriptId': 'y',
        'timestamp': 'not-a-date',
        'marks': <dynamic>[],
        'notes': <dynamic>[],
      };
      expect(() => AnnotationSnapshot.fromJson(json), throwsFormatException);
    });
  });
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd horatio_core && dart test test/models/model_test.dart -v
```

- [ ] **Step 3: Create AnnotationSnapshot model**

Create `horatio_core/lib/src/models/annotation_snapshot.dart`:

```dart
import 'package:meta/meta.dart';

import 'package:horatio_core/src/models/line_note.dart';
import 'package:horatio_core/src/models/text_mark.dart';

/// A point-in-time record of all annotations for a script.
///
/// Enables change history, undo, and viewing annotation evolution over time.
@immutable
final class AnnotationSnapshot {
  /// Creates an [AnnotationSnapshot] with unmodifiable lists.
  AnnotationSnapshot({
    required this.id,
    required this.scriptId,
    required this.timestamp,
    required List<TextMark> marks,
    required List<LineNote> notes,
  }) : marks = List.unmodifiable(marks),
       notes = List.unmodifiable(notes);

  /// Unique identifier (UUID).
  final String id;

  /// The script these annotations belong to.
  final String scriptId;

  /// When this snapshot was taken.
  final DateTime timestamp;

  /// All text marks at snapshot time.
  final List<TextMark> marks;

  /// All line notes at snapshot time.
  final List<LineNote> notes;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AnnotationSnapshot && id == other.id;

  @override
  int get hashCode => id.hashCode;

  /// Serializes to a JSON-compatible map.
  Map<String, dynamic> toJson() => {
    'id': id,
    'scriptId': scriptId,
    'timestamp': timestamp.toUtc().toIso8601String(),
    'marks': marks.map((m) => m.toJson()).toList(),
    'notes': notes.map((n) => n.toJson()).toList(),
  };

  /// Deserializes from a JSON map.
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

- [ ] **Step 4: Add export and run tests**

Add `export 'annotation_snapshot.dart';` to `models.dart`, then:

```bash
cd horatio_core && dart test test/models/model_test.dart -v
```

Expected: all AnnotationSnapshot tests pass.

- [ ] **Step 5: Run full core test suite with coverage**

```bash
cd horatio_core && dart run coverage:test_with_coverage
```

Check coverage is still 100%.

- [ ] **Step 6: Commit**

```bash
git add horatio_core/lib/src/models/annotation_snapshot.dart \
        horatio_core/lib/src/models/models.dart \
        horatio_core/test/models/model_test.dart
git commit -m "feat(core): add AnnotationSnapshot model with serialization"
```

---

## Chunk 2: Drift Database + DAO + uuid app dep

### Task 7: Add drift_dev, build_runner, and uuid to app dependencies

**Files:**

- Modify: `horatio_app/pubspec.yaml`

- [ ] **Step 1: Add dev dependencies and uuid**

Add `build_runner`, `drift_dev` (dev deps) and `uuid` (regular dep) to
`horatio_app/pubspec.yaml`. `uuid` is needed by the annotation cubits in
Chunk 3:

```yaml
dependencies:
  # ... existing deps ...
  uuid: ^4.5.1

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^6.0.0
  bloc_test: ^10.0.0
  mocktail: ^1.0.0
  plugin_platform_interface: any
  build_runner: ^2.4.0
  drift_dev: ^2.22.0
```

- [ ] **Step 2: Run flutter pub get**

```bash
cd horatio_app && flutter pub get
```

Expected: resolves successfully.

- [ ] **Step 3: Commit**

```bash
git add horatio_app/pubspec.yaml horatio_app/pubspec.lock
git commit -m "chore(app): add build_runner, drift_dev, uuid dependencies"
```

---

### Task 8: Create drift database and annotation tables

**Files:**

- Create: `horatio_app/lib/database/tables/text_marks_table.dart`
- Create: `horatio_app/lib/database/tables/line_notes_table.dart`
- Create: `horatio_app/lib/database/tables/annotation_snapshots_table.dart`
- Create: `horatio_app/lib/database/app_database.dart`

> **`.g.dart` strategy:** Generated files (`app_database.g.dart`) should be
> **committed** to the repository. This avoids requiring CI to install
> build_runner and ensures every commit compiles. The run.sh codegen step
> (Task 14) refreshes them, and the cache hash excludes `.g.dart` files.
> If strict lints flag generated code, add `analyzer: exclude: ['**/*.g.dart']`
> to `horatio_app/analysis_options.yaml`.

- [ ] **Step 1: Create text_marks table**

Create `horatio_app/lib/database/tables/text_marks_table.dart`:

```dart
import 'package:drift/drift.dart';

/// Drift table for text-level delivery marks on script lines.
class TextMarksTable extends Table {
  @override
  String get tableName => 'text_marks';

  TextColumn get id => text()();
  TextColumn get scriptId => text()();
  IntColumn get lineIndex => integer()();
  IntColumn get startOffset => integer()();
  IntColumn get endOffset => integer()();
  TextColumn get markType => text()();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}
```

- [ ] **Step 2: Create line_notes table**

Create `horatio_app/lib/database/tables/line_notes_table.dart`:

```dart
import 'package:drift/drift.dart';

/// Drift table for line-level interpretive notes.
class LineNotesTable extends Table {
  @override
  String get tableName => 'line_notes';

  TextColumn get id => text()();
  TextColumn get scriptId => text()();
  IntColumn get lineIndex => integer()();
  TextColumn get category => text()();
  TextColumn get noteText => text()();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}
```

- [ ] **Step 3: Create annotation_snapshots table**

Create `horatio_app/lib/database/tables/annotation_snapshots_table.dart`:

```dart
import 'package:drift/drift.dart';

/// Drift table for annotation history snapshots.
class AnnotationSnapshotsTable extends Table {
  @override
  String get tableName => 'annotation_snapshots';

  TextColumn get id => text()();
  TextColumn get scriptId => text()();
  DateTimeColumn get timestamp => dateTime()();
  TextColumn get snapshotJson => text()();

  @override
  Set<Column> get primaryKey => {id};
}
```

- [ ] **Step 4: Create app database**

Create `horatio_app/lib/database/app_database.dart`:

```dart
import 'package:drift/drift.dart';
import 'package:horatio_app/database/tables/annotation_snapshots_table.dart';
import 'package:horatio_app/database/tables/line_notes_table.dart';
import 'package:horatio_app/database/tables/text_marks_table.dart';

part 'app_database.g.dart';

/// Central drift database for Horatio.
///
/// Schema version 1: annotation tables (text_marks, line_notes,
/// annotation_snapshots).
@DriftDatabase(
  tables: [TextMarksTable, LineNotesTable, AnnotationSnapshotsTable],
)
class AppDatabase extends _$AppDatabase {
  /// Creates an [AppDatabase] with the given [QueryExecutor].
  AppDatabase(super.e);

  @override
  int get schemaVersion => 1;
}
```

> **Note:** The `daos: [AnnotationDao]` parameter is NOT added here because
> AnnotationDao doesn't exist yet (created in Task 9). Task 9 Step 1 will
> add the import and `daos:` list to AppDatabase.

- [ ] **Step 5: Commit (before codegen — tables only)**

```bash
git add horatio_app/lib/database/
git commit -m "feat(app): add drift table definitions for annotations"
```

---

### Task 9: Create AnnotationDao

**Files:**

- Create: `horatio_app/lib/database/daos/annotation_dao.dart`

- [ ] **Step 1: Register DAO in AppDatabase**

Update `horatio_app/lib/database/app_database.dart` to add the import and DAO
registration:

```dart
import 'package:horatio_app/database/daos/annotation_dao.dart';
```

And update the `@DriftDatabase` annotation:

```dart
@DriftDatabase(
  tables: [TextMarksTable, LineNotesTable, AnnotationSnapshotsTable],
  daos: [AnnotationDao],
)
```

- [ ] **Step 2: Create the DAO**

Create `horatio_app/lib/database/daos/annotation_dao.dart`:

```dart
import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/tables/annotation_snapshots_table.dart';
import 'package:horatio_app/database/tables/line_notes_table.dart';
import 'package:horatio_app/database/tables/text_marks_table.dart';
import 'package:horatio_core/horatio_core.dart';

part 'annotation_dao.g.dart';

/// Data access object for annotation persistence.
///
/// [TextMark] and [LineNote] models do not carry a [scriptId] field —
/// the DAO binds it at the persistence boundary.
@DriftAccessor(
  tables: [TextMarksTable, LineNotesTable, AnnotationSnapshotsTable],
)
class AnnotationDao extends DatabaseAccessor<AppDatabase>
    with _$AnnotationDaoMixin {
  /// Creates an [AnnotationDao].
  AnnotationDao(super.db);

  // -- TextMark CRUD --------------------------------------------------------

  /// Watches all marks for a script.
  Stream<List<TextMark>> watchMarksForScript(String scriptId) =>
      (select(textMarksTable)
            ..where((t) => t.scriptId.equals(scriptId))
            ..orderBy([(t) => OrderingTerm.asc(t.lineIndex)]))
          .watch()
          .map((rows) => rows.map(_rowToMark).toList());

  /// Gets marks for a specific line.
  Future<List<TextMark>> getMarksForLine(
    String scriptId,
    int lineIndex,
  ) async {
    final rows = await (select(textMarksTable)
          ..where(
            (t) =>
                t.scriptId.equals(scriptId) &
                t.lineIndex.equals(lineIndex),
          ))
        .get();
    return rows.map(_rowToMark).toList();
  }

  /// Inserts a text mark.
  Future<void> insertMark(String scriptId, TextMark mark) => into(
        textMarksTable,
      ).insert(
        TextMarksTableCompanion.insert(
          id: mark.id,
          scriptId: scriptId,
          lineIndex: mark.lineIndex,
          startOffset: mark.startOffset,
          endOffset: mark.endOffset,
          markType: mark.type.name,
          createdAt: mark.createdAt,
        ),
      );

  /// Deletes a text mark by ID.
  Future<void> deleteMark(String id) =>
      (delete(textMarksTable)..where((t) => t.id.equals(id))).go();

  TextMark _rowToMark(TextMarksTableData row) => TextMark(
        id: row.id,
        lineIndex: row.lineIndex,
        startOffset: row.startOffset,
        endOffset: row.endOffset,
        type: MarkType.values.byName(row.markType),
        createdAt: row.createdAt,
      );

  // -- LineNote CRUD --------------------------------------------------------

  /// Watches all notes for a script.
  Stream<List<LineNote>> watchNotesForScript(String scriptId) =>
      (select(lineNotesTable)
            ..where((t) => t.scriptId.equals(scriptId))
            ..orderBy([(t) => OrderingTerm.asc(t.lineIndex)]))
          .watch()
          .map((rows) => rows.map(_rowToNote).toList());

  /// Gets notes for a specific line.
  Future<List<LineNote>> getNotesForLine(
    String scriptId,
    int lineIndex,
  ) async {
    final rows = await (select(lineNotesTable)
          ..where(
            (t) =>
                t.scriptId.equals(scriptId) &
                t.lineIndex.equals(lineIndex),
          ))
        .get();
    return rows.map(_rowToNote).toList();
  }

  /// Inserts a line note.
  Future<void> insertNote(String scriptId, LineNote note) => into(
        lineNotesTable,
      ).insert(
        LineNotesTableCompanion.insert(
          id: note.id,
          scriptId: scriptId,
          lineIndex: note.lineIndex,
          category: note.category.name,
          noteText: note.text,
          createdAt: note.createdAt,
        ),
      );

  /// Updates the text of a note.
  Future<void> updateNoteText(String id, String text) =>
      (update(lineNotesTable)..where((t) => t.id.equals(id)))
          .write(LineNotesTableCompanion(noteText: Value(text)));

  /// Deletes a note by ID.
  Future<void> deleteNote(String id) =>
      (delete(lineNotesTable)..where((t) => t.id.equals(id))).go();

  LineNote _rowToNote(LineNotesTableData row) => LineNote(
        id: row.id,
        lineIndex: row.lineIndex,
        category: NoteCategory.values.byName(row.category),
        text: row.noteText,
        createdAt: row.createdAt,
      );

  // -- Snapshot management --------------------------------------------------

  /// Watches all snapshots for a script, newest first.
  Stream<List<AnnotationSnapshot>> watchSnapshotsForScript(
    String scriptId,
  ) =>
      (select(annotationSnapshotsTable)
            ..where((t) => t.scriptId.equals(scriptId))
            ..orderBy([(t) => OrderingTerm.desc(t.timestamp)]))
          .watch()
          .map((rows) => rows.map(_rowToSnapshot).toList());

  /// Inserts a snapshot.
  Future<void> insertSnapshot(AnnotationSnapshot snapshot) => into(
        annotationSnapshotsTable,
      ).insert(
        AnnotationSnapshotsTableCompanion.insert(
          id: snapshot.id,
          scriptId: snapshot.scriptId,
          timestamp: snapshot.timestamp,
          snapshotJson: json.encode(snapshot.toJson()),
        ),
      );

  AnnotationSnapshot _rowToSnapshot(AnnotationSnapshotsTableData row) =>
      AnnotationSnapshot.fromJson(
        json.decode(row.snapshotJson) as Map<String, dynamic>,
      );
      // Note: scriptId and timestamp exist in both the table columns (for
      // efficient WHERE/ORDER BY filtering) AND in the JSON blob (for complete
      // deserialization). The columns are the source of truth for queries;
      // the JSON is the source of truth for the full snapshot data.

  // -- Bulk operations (for snapshot restore) -------------------------------

  /// Deletes ALL marks and notes for a script, then inserts the given ones.
  /// Used by snapshot restore.
  Future<void> replaceAllAnnotations({
    required String scriptId,
    required List<TextMark> marks,
    required List<LineNote> notes,
  }) => transaction(() async {
    await (delete(textMarksTable)
          ..where((t) => t.scriptId.equals(scriptId)))
        .go();
    await (delete(lineNotesTable)
          ..where((t) => t.scriptId.equals(scriptId)))
        .go();
    for (final mark in marks) {
      await insertMark(scriptId, mark);
    }
    for (final note in notes) {
      await insertNote(scriptId, note);
    }
  });
}
```

- [ ] **Step 3: Run drift codegen**

```bash
cd horatio_app && dart run build_runner build --delete-conflicting-outputs
```

Expected: generates `app_database.g.dart` and `annotation_dao.g.dart`.

- [ ] **Step 4: Run analysis**

```bash
cd horatio_app && flutter analyze --fatal-infos
```

Expected: no issues.

- [ ] **Step 5: Commit**

```bash
git add horatio_app/lib/database/
git commit -m "feat(app): add AnnotationDao with drift codegen"
```

---

### Task 10: Write DAO tests

**Files:**

- Create: `horatio_app/test/database/annotation_dao_test.dart`

- [ ] **Step 1: Write comprehensive DAO tests**

Create `horatio_app/test/database/annotation_dao_test.dart`:

```dart
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  late AppDatabase db;
  late AnnotationDao dao;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    dao = db.annotationDao;
  });

  tearDown(() => db.close());

  const scriptId = 'script-uuid-1';

  TextMark makeMark({
    String id = 'm1',
    int lineIndex = 0,
    int startOffset = 0,
    int endOffset = 5,
    MarkType type = MarkType.stress,
  }) =>
      TextMark(
        id: id,
        lineIndex: lineIndex,
        startOffset: startOffset,
        endOffset: endOffset,
        type: type,
        createdAt: DateTime.utc(2026, 3, 29),
      );

  LineNote makeNote({
    String id = 'n1',
    int lineIndex = 0,
    NoteCategory category = NoteCategory.intention,
    String text = 'test note',
  }) =>
      LineNote(
        id: id,
        lineIndex: lineIndex,
        category: category,
        text: text,
        createdAt: DateTime.utc(2026, 3, 29),
      );

  group('TextMark CRUD', () {
    test('insertMark and getMarksForLine', () async {
      await dao.insertMark(scriptId, makeMark());
      final marks = await dao.getMarksForLine(scriptId, 0);
      expect(marks.length, 1);
      expect(marks.first.id, 'm1');
      expect(marks.first.type, MarkType.stress);
    });

    test('deleteMark removes mark', () async {
      await dao.insertMark(scriptId, makeMark());
      await dao.deleteMark('m1');
      final marks = await dao.getMarksForLine(scriptId, 0);
      expect(marks, isEmpty);
    });

    test('watchMarksForScript emits on insert', () async {
      final stream = dao.watchMarksForScript(scriptId);
      // First emission: empty
      expectLater(
        stream,
        emitsInOrder([
          isEmpty,
          hasLength(1),
        ]),
      );
      await dao.insertMark(scriptId, makeMark());
    });

    test('getMarksForLine filters by scriptId', () async {
      await dao.insertMark(scriptId, makeMark());
      await dao.insertMark('other-script', makeMark(id: 'm2'));
      final marks = await dao.getMarksForLine(scriptId, 0);
      expect(marks.length, 1);
      expect(marks.first.id, 'm1');
    });
  });

  group('LineNote CRUD', () {
    test('insertNote and getNotesForLine', () async {
      await dao.insertNote(scriptId, makeNote());
      final notes = await dao.getNotesForLine(scriptId, 0);
      expect(notes.length, 1);
      expect(notes.first.text, 'test note');
    });

    test('updateNoteText modifies text', () async {
      await dao.insertNote(scriptId, makeNote());
      await dao.updateNoteText('n1', 'updated text');
      final notes = await dao.getNotesForLine(scriptId, 0);
      expect(notes.first.text, 'updated text');
    });

    test('deleteNote removes note', () async {
      await dao.insertNote(scriptId, makeNote());
      await dao.deleteNote('n1');
      final notes = await dao.getNotesForLine(scriptId, 0);
      expect(notes, isEmpty);
    });

    test('watchNotesForScript emits on insert', () async {
      final stream = dao.watchNotesForScript(scriptId);
      expectLater(
        stream,
        emitsInOrder([isEmpty, hasLength(1)]),
      );
      await dao.insertNote(scriptId, makeNote());
    });
  });

  group('Snapshot management', () {
    test('insertSnapshot and watch', () async {
      final snapshot = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: scriptId,
        timestamp: DateTime.utc(2026, 3, 29),
        marks: [makeMark()],
        notes: [makeNote()],
      );
      final stream = dao.watchSnapshotsForScript(scriptId);
      expectLater(
        stream,
        emitsInOrder([isEmpty, hasLength(1)]),
      );
      await dao.insertSnapshot(snapshot);
    });
  });

  group('replaceAllAnnotations', () {
    test('deletes existing and inserts new', () async {
      await dao.insertMark(scriptId, makeMark(id: 'old-m'));
      await dao.insertNote(scriptId, makeNote(id: 'old-n'));

      await dao.replaceAllAnnotations(
        scriptId: scriptId,
        marks: [makeMark(id: 'new-m')],
        notes: [makeNote(id: 'new-n', text: 'new note')],
      );

      final marks = await dao.getMarksForLine(scriptId, 0);
      expect(marks.length, 1);
      expect(marks.first.id, 'new-m');

      final notes = await dao.getNotesForLine(scriptId, 0);
      expect(notes.length, 1);
      expect(notes.first.id, 'new-n');
    });

    test('does not affect other scripts', () async {
      await dao.insertMark('other-script', makeMark(id: 'keep-m'));
      await dao.replaceAllAnnotations(
        scriptId: scriptId,
        marks: [],
        notes: [],
      );
      final marks = await dao.getMarksForLine('other-script', 0);
      expect(marks.length, 1);
      expect(marks.first.id, 'keep-m');
    });
  });
}
```

- [ ] **Step 2: Run DAO tests**

```bash
cd horatio_app && flutter test test/database/annotation_dao_test.dart -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add horatio_app/test/database/
git commit -m "test(app): add comprehensive AnnotationDao tests"
```

---

## Chunk 3: Cubits

### Task 11: Create AnnotationCubit

**Files:**

- Create: `horatio_app/lib/bloc/annotation/annotation_state.dart`
- Create: `horatio_app/lib/bloc/annotation/annotation_cubit.dart`
- Create: `horatio_app/test/bloc/annotation_cubit_test.dart`

- [ ] **Step 1: Write test file**

Create `horatio_app/test/bloc/annotation_cubit_test.dart`:

```dart
import 'dart:async';

import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/annotation/annotation_cubit.dart';
import 'package:horatio_app/bloc/annotation/annotation_state.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockAnnotationDao extends Mock implements AnnotationDao {}

void main() {
  late MockAnnotationDao dao;
  late StreamController<List<TextMark>> marksController;
  late StreamController<List<LineNote>> notesController;

  const scriptId = 'script-1';

  final testMark = TextMark(
    id: 'm1',
    lineIndex: 0,
    startOffset: 0,
    endOffset: 5,
    type: MarkType.stress,
    createdAt: DateTime.utc(2026),
  );

  final testNote = LineNote(
    id: 'n1',
    lineIndex: 0,
    category: NoteCategory.intention,
    text: 'test',
    createdAt: DateTime.utc(2026),
  );

  setUp(() {
    dao = MockAnnotationDao();
    marksController = StreamController<List<TextMark>>.broadcast();
    notesController = StreamController<List<LineNote>>.broadcast();

    when(() => dao.watchMarksForScript(scriptId))
        .thenAnswer((_) => marksController.stream);
    when(() => dao.watchNotesForScript(scriptId))
        .thenAnswer((_) => notesController.stream);
  });

  tearDown(() {
    marksController.close();
    notesController.close();
  });

  setUpAll(() {
    registerFallbackValue(testMark);
    registerFallbackValue(testNote);
  });

  group('AnnotationCubit', () {
    test('initial state is AnnotationInitial', () {
      final cubit = AnnotationCubit(dao: dao);
      expect(cubit.state, isA<AnnotationInitial>());
      cubit.close();
    });

    test('loadAnnotations subscribes and emits on marks stream', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([testMark]);
      await Future<void>.delayed(Duration.zero);
      final state = cubit.state;
      expect(state, isA<AnnotationLoaded>());
      expect((state as AnnotationLoaded).marks, [testMark]);
      await cubit.close();
    });

    test('loadAnnotations subscribes and emits on notes stream', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      notesController.add([testNote]);
      await Future<void>.delayed(Duration.zero);
      final state = cubit.state;
      expect(state, isA<AnnotationLoaded>());
      expect((state as AnnotationLoaded).notes, [testNote]);
      await cubit.close();
    });

    test('loadAnnotations double-emits on both streams', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([testMark]);
      notesController.add([testNote]);
      await Future<void>.delayed(Duration.zero);
      final state = cubit.state as AnnotationLoaded;
      expect(state.marks, [testMark]);
      expect(state.notes, [testNote]);
      await cubit.close();
    });

    test('selectLine updates selectedLineIndex', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([]);
      await Future<void>.delayed(Duration.zero);
      cubit.selectLine(3);
      expect((cubit.state as AnnotationLoaded).selectedLineIndex, 3);
      await cubit.close();
    });

    test('selectLine is no-op when state is AnnotationInitial', () {
      final cubit = AnnotationCubit(dao: dao);
      cubit.selectLine(3); // Should not throw
      expect(cubit.state, isA<AnnotationInitial>());
      cubit.close();
    });

    test('startEditing / cancelEditing toggle EditingContext', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([]);
      await Future<void>.delayed(Duration.zero);

      cubit.startEditing(lineIndex: 2, isAddingMark: true);
      final editing = (cubit.state as AnnotationLoaded).editing;
      expect(editing, isNotNull);
      expect(editing!.lineIndex, 2);
      expect(editing.isAddingMark, isTrue);

      cubit.cancelEditing();
      expect((cubit.state as AnnotationLoaded).editing, isNull);
      await cubit.close();
    });

    test('startEditing is no-op when state is AnnotationInitial', () {
      final cubit = AnnotationCubit(dao: dao);
      cubit.startEditing(lineIndex: 0, isAddingMark: true);
      expect(cubit.state, isA<AnnotationInitial>());
      cubit.close();
    });

    test('cancelEditing is no-op when state is AnnotationInitial', () {
      final cubit = AnnotationCubit(dao: dao);
      cubit.cancelEditing();
      expect(cubit.state, isA<AnnotationInitial>());
      cubit.close();
    });

    test('selectedLineIndex preserved across stream updates', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([]);
      await Future<void>.delayed(Duration.zero);
      cubit.selectLine(5);
      marksController.add([testMark]); // stream update
      await Future<void>.delayed(Duration.zero);
      expect((cubit.state as AnnotationLoaded).selectedLineIndex, 5);
      await cubit.close();
    });

    test('addMark calls dao.insertMark', () async {
      when(() => dao.insertMark(any(), any())).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.addMark(
        lineIndex: 0,
        startOffset: 0,
        endOffset: 5,
        type: MarkType.stress,
      );
      verify(() => dao.insertMark(scriptId, any())).called(1);
      await cubit.close();
    });

    test('addMark is no-op when scriptId is null', () async {
      final cubit = AnnotationCubit(dao: dao);
      await cubit.addMark(
        lineIndex: 0,
        startOffset: 0,
        endOffset: 5,
        type: MarkType.stress,
      );
      verifyNever(() => dao.insertMark(any(), any()));
      await cubit.close();
    });

    test('removeMark calls dao.deleteMark', () async {
      when(() => dao.deleteMark('m1')).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao);
      await cubit.removeMark('m1');
      verify(() => dao.deleteMark('m1')).called(1);
      await cubit.close();
    });

    test('addNote calls dao.insertNote', () async {
      when(() => dao.insertNote(any(), any())).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.addNote(
        lineIndex: 0,
        category: NoteCategory.intention,
        text: 'test note',
      );
      verify(() => dao.insertNote(scriptId, any())).called(1);
      await cubit.close();
    });

    test('addNote is no-op when scriptId is null', () async {
      final cubit = AnnotationCubit(dao: dao);
      await cubit.addNote(
        lineIndex: 0,
        category: NoteCategory.intention,
        text: 'test',
      );
      verifyNever(() => dao.insertNote(any(), any()));
      await cubit.close();
    });

    test('updateNote calls dao.updateNoteText', () async {
      when(() => dao.updateNoteText('n1', 'new'))
          .thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao);
      await cubit.updateNote('n1', 'new');
      verify(() => dao.updateNoteText('n1', 'new')).called(1);
      await cubit.close();
    });

    test('removeNote calls dao.deleteNote', () async {
      when(() => dao.deleteNote('n1')).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao);
      await cubit.removeNote('n1');
      verify(() => dao.deleteNote('n1')).called(1);
      await cubit.close();
    });

    test('loadAnnotations with new scriptId cancels previous streams',
        () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([testMark]);
      await Future<void>.delayed(Duration.zero);

      final marks2 = StreamController<List<TextMark>>.broadcast();
      final notes2 = StreamController<List<LineNote>>.broadcast();
      when(() => dao.watchMarksForScript('script-2'))
          .thenAnswer((_) => marks2.stream);
      when(() => dao.watchNotesForScript('script-2'))
          .thenAnswer((_) => notes2.stream);

      cubit.loadAnnotations('script-2');
      marks2.add([]);
      notes2.add([]);
      await Future<void>.delayed(Duration.zero);

      final state = cubit.state;
      expect(state, isA<AnnotationLoaded>());
      expect((state as AnnotationLoaded).scriptId, 'script-2');
      expect(state.marks, isEmpty);

      await cubit.close();
      await marks2.close();
      await notes2.close();
    });

    test('close cancels stream subscriptions', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      await cubit.close();
      // Adding to controller after close should not cause errors.
      marksController.add([]);
      notesController.add([]);
    });
  });
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd horatio_app && flutter test test/bloc/annotation_cubit_test.dart -v
```

- [ ] **Step 3: Create annotation_state.dart**

Create `horatio_app/lib/bloc/annotation/annotation_state.dart`:

```dart
import 'package:equatable/equatable.dart';
import 'package:flutter/foundation.dart';
import 'package:horatio_core/horatio_core.dart';

/// State for [AnnotationCubit].
sealed class AnnotationState extends Equatable {
  const AnnotationState();
}

/// No annotations loaded.
final class AnnotationInitial extends AnnotationState {
  const AnnotationInitial();

  @override
  List<Object?> get props => [];
}

/// Annotations loaded for a script.
final class AnnotationLoaded extends AnnotationState {
  const AnnotationLoaded({
    required this.scriptId,
    required this.marks,
    required this.notes,
    this.selectedLineIndex,
    this.editing,
  });

  /// The script these annotations belong to.
  final String scriptId;

  /// All text marks for this script.
  final List<TextMark> marks;

  /// All line notes for this script.
  final List<LineNote> notes;

  /// Currently selected line index (nullable).
  final int? selectedLineIndex;

  /// Non-null when actively editing.
  final EditingContext? editing;

  /// Creates a copy with specified fields replaced.
  AnnotationLoaded copyWith({
    List<TextMark>? marks,
    List<LineNote>? notes,
    int? Function()? selectedLineIndex,
    EditingContext? Function()? editing,
  }) => AnnotationLoaded(
    scriptId: scriptId,
    marks: marks ?? this.marks,
    notes: notes ?? this.notes,
    selectedLineIndex: selectedLineIndex != null
        ? selectedLineIndex()
        : this.selectedLineIndex,
    editing: editing != null ? editing() : this.editing,
  );

  @override
  List<Object?> get props =>
      [scriptId, marks, notes, selectedLineIndex, editing];
}

/// Context for an active annotation edit.
@immutable
final class EditingContext extends Equatable {
  const EditingContext({
    required this.lineIndex,
    required this.isAddingMark,
  });

  /// The line being edited.
  final int lineIndex;

  /// Whether placing a mark (true) or writing a note (false).
  final bool isAddingMark;

  @override
  List<Object?> get props => [lineIndex, isAddingMark];
}
```

- [ ] **Step 4: Create annotation_cubit.dart**

Create `horatio_app/lib/bloc/annotation/annotation_cubit.dart`:

```dart
import 'dart:async';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/annotation/annotation_state.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:uuid/uuid.dart';

/// Manages annotation CRUD for a script.
class AnnotationCubit extends Cubit<AnnotationState> {
  /// Creates an [AnnotationCubit].
  AnnotationCubit({required AnnotationDao dao})
      : _dao = dao,
        super(const AnnotationInitial());

  final AnnotationDao _dao;
  StreamSubscription<List<TextMark>>? _marksSub;
  StreamSubscription<List<LineNote>>? _notesSub;
  String? _scriptId;

  static const _uuid = Uuid();

  /// Subscribes to annotation streams for a script.
  void loadAnnotations(String scriptId) {
    _scriptId = scriptId;
    _marksSub?.cancel();
    _notesSub?.cancel();

    List<TextMark> latestMarks = [];
    List<LineNote> latestNotes = [];

    _marksSub = _dao.watchMarksForScript(scriptId).listen((marks) {
      latestMarks = marks;
      _emitLoaded(scriptId, latestMarks, latestNotes);
    });

    _notesSub = _dao.watchNotesForScript(scriptId).listen((notes) {
      latestNotes = notes;
      _emitLoaded(scriptId, latestMarks, latestNotes);
    });
  }

  void _emitLoaded(
    String scriptId,
    List<TextMark> marks,
    List<LineNote> notes,
  ) {
    final current = state;
    emit(AnnotationLoaded(
      scriptId: scriptId,
      marks: marks,
      notes: notes,
      selectedLineIndex:
          current is AnnotationLoaded ? current.selectedLineIndex : null,
      editing: current is AnnotationLoaded ? current.editing : null,
    ));
  }

  /// Focuses a line for annotation.
  void selectLine(int? lineIndex) {
    final current = state;
    if (current is AnnotationLoaded) {
      emit(current.copyWith(selectedLineIndex: () => lineIndex));
    }
  }

  /// Enters editing mode.
  void startEditing({required int lineIndex, required bool isAddingMark}) {
    final current = state;
    if (current is AnnotationLoaded) {
      emit(current.copyWith(
        selectedLineIndex: () => lineIndex,
        editing: () => EditingContext(
          lineIndex: lineIndex,
          isAddingMark: isAddingMark,
        ),
      ));
    }
  }

  /// Exits editing mode.
  void cancelEditing() {
    final current = state;
    if (current is AnnotationLoaded) {
      emit(current.copyWith(editing: () => null));
    }
  }

  /// Adds a text mark.
  Future<void> addMark({
    required int lineIndex,
    required int startOffset,
    required int endOffset,
    required MarkType type,
  }) async {
    final scriptId = _scriptId;
    if (scriptId == null) return;
    final mark = TextMark(
      id: _uuid.v4(),
      lineIndex: lineIndex,
      startOffset: startOffset,
      endOffset: endOffset,
      type: type,
      createdAt: DateTime.now().toUtc(),
    );
    await _dao.insertMark(scriptId, mark);
  }

  /// Removes a text mark.
  Future<void> removeMark(String id) => _dao.deleteMark(id);

  /// Adds a line note.
  Future<void> addNote({
    required int lineIndex,
    required NoteCategory category,
    required String text,
  }) async {
    final scriptId = _scriptId;
    if (scriptId == null) return;
    final note = LineNote(
      id: _uuid.v4(),
      lineIndex: lineIndex,
      category: category,
      text: text,
      createdAt: DateTime.now().toUtc(),
    );
    await _dao.insertNote(scriptId, note);
  }

  /// Updates a note's text.
  Future<void> updateNote(String id, String text) =>
      _dao.updateNoteText(id, text);

  /// Removes a note.
  Future<void> removeNote(String id) => _dao.deleteNote(id);

  @override
  Future<void> close() {
    _marksSub?.cancel();
    _notesSub?.cancel();
    return super.close();
  }
}
```

- [ ] **Step 5: Run tests**

```bash
cd horatio_app && flutter test test/bloc/annotation_cubit_test.dart -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add horatio_app/lib/bloc/annotation/ horatio_app/test/bloc/annotation_cubit_test.dart
git commit -m "feat(app): add AnnotationCubit with CRUD operations"
```

---

### Task 12: Create AnnotationHistoryCubit

**Files:**

- Create: `horatio_app/lib/bloc/annotation/annotation_history_state.dart`
- Create: `horatio_app/lib/bloc/annotation/annotation_history_cubit.dart`
- Create: `horatio_app/test/bloc/annotation_history_cubit_test.dart`

- [ ] **Step 1: Write tests**

Create `horatio_app/test/bloc/annotation_history_cubit_test.dart`:

```dart
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/annotation/annotation_history_cubit.dart';
import 'package:horatio_app/bloc/annotation/annotation_history_state.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockAnnotationDao extends Mock implements AnnotationDao {}

void main() {
  late MockAnnotationDao dao;
  late StreamController<List<AnnotationSnapshot>> snapshotsController;

  const scriptId = 'script-1';

  final testMark = TextMark(
    id: 'm1',
    lineIndex: 0,
    startOffset: 0,
    endOffset: 5,
    type: MarkType.stress,
    createdAt: DateTime.utc(2026),
  );

  final testNote = LineNote(
    id: 'n1',
    lineIndex: 0,
    category: NoteCategory.intention,
    text: 'test',
    createdAt: DateTime.utc(2026),
  );

  final testSnapshot = AnnotationSnapshot(
    id: 'snap-1',
    scriptId: scriptId,
    timestamp: DateTime.utc(2026, 3, 29),
    marks: [testMark],
    notes: [testNote],
  );

  setUp(() {
    dao = MockAnnotationDao();
    snapshotsController =
        StreamController<List<AnnotationSnapshot>>.broadcast();
    when(() => dao.watchSnapshotsForScript(scriptId))
        .thenAnswer((_) => snapshotsController.stream);
  });

  tearDown(() => snapshotsController.close());

  setUpAll(() {
    registerFallbackValue(testSnapshot);
  });

  group('AnnotationHistoryCubit', () {
    test('initial state is AnnotationHistoryInitial', () {
      final cubit = AnnotationHistoryCubit(dao: dao);
      expect(cubit.state, isA<AnnotationHistoryInitial>());
      cubit.close();
    });

    test('loadSnapshots subscribes and emits AnnotationHistoryLoaded',
        () async {
      final cubit = AnnotationHistoryCubit(dao: dao)
        ..loadSnapshots(scriptId);
      snapshotsController.add([testSnapshot]);
      await Future<void>.delayed(Duration.zero);
      final state = cubit.state;
      expect(state, isA<AnnotationHistoryLoaded>());
      expect((state as AnnotationHistoryLoaded).snapshots, [testSnapshot]);
      await cubit.close();
    });

    test('saveSnapshot calls dao.insertSnapshot with correct data', () async {
      when(() => dao.insertSnapshot(any())).thenAnswer((_) async {});
      final cubit = AnnotationHistoryCubit(dao: dao)
        ..loadSnapshots(scriptId);
      snapshotsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.saveSnapshot(marks: [testMark], notes: [testNote]);
      final captured =
          verify(() => dao.insertSnapshot(captureAny())).captured.single
              as AnnotationSnapshot;
      expect(captured.scriptId, scriptId);
      expect(captured.marks, [testMark]);
      expect(captured.notes, [testNote]);
      await cubit.close();
    });

    test('saveSnapshot is no-op when scriptId is null', () async {
      final cubit = AnnotationHistoryCubit(dao: dao);
      await cubit.saveSnapshot(marks: [], notes: []);
      verifyNever(() => dao.insertSnapshot(any()));
      await cubit.close();
    });

    test('restoreSnapshot calls dao.replaceAllAnnotations', () async {
      when(
        () => dao.replaceAllAnnotations(
          scriptId: any(named: 'scriptId'),
          marks: any(named: 'marks'),
          notes: any(named: 'notes'),
        ),
      ).thenAnswer((_) async {});
      final cubit = AnnotationHistoryCubit(dao: dao)
        ..loadSnapshots(scriptId);
      snapshotsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.restoreSnapshot(testSnapshot);
      verify(
        () => dao.replaceAllAnnotations(
          scriptId: scriptId,
          marks: testSnapshot.marks,
          notes: testSnapshot.notes,
        ),
      ).called(1);
      await cubit.close();
    });

    test('restoreSnapshot is no-op when scriptId is null', () async {
      final cubit = AnnotationHistoryCubit(dao: dao);
      await cubit.restoreSnapshot(testSnapshot);
      verifyNever(
        () => dao.replaceAllAnnotations(
          scriptId: any(named: 'scriptId'),
          marks: any(named: 'marks'),
          notes: any(named: 'notes'),
        ),
      );
      await cubit.close();
    });

    test('loadSnapshots with new scriptId cancels previous stream', () async {
      final cubit = AnnotationHistoryCubit(dao: dao)
        ..loadSnapshots(scriptId);
      snapshotsController.add([testSnapshot]);
      await Future<void>.delayed(Duration.zero);

      final snapshots2 = StreamController<List<AnnotationSnapshot>>.broadcast();
      when(() => dao.watchSnapshotsForScript('script-2'))
          .thenAnswer((_) => snapshots2.stream);

      cubit.loadSnapshots('script-2');
      snapshots2.add([]);
      await Future<void>.delayed(Duration.zero);

      final state = cubit.state;
      expect(state, isA<AnnotationHistoryLoaded>());
      expect((state as AnnotationHistoryLoaded).snapshots, isEmpty);

      await cubit.close();
      await snapshots2.close();
    });

    test('close cancels stream subscription', () async {
      final cubit = AnnotationHistoryCubit(dao: dao)
        ..loadSnapshots(scriptId);
      await cubit.close();
      snapshotsController.add([testSnapshot]);
      // Should not cause errors.
    });
  });
}
```

- [ ] **Step 2: Create state file**

Create `horatio_app/lib/bloc/annotation/annotation_history_state.dart`:

```dart
import 'package:equatable/equatable.dart';
import 'package:horatio_core/horatio_core.dart';

/// State for [AnnotationHistoryCubit].
sealed class AnnotationHistoryState extends Equatable {
  const AnnotationHistoryState();
}

/// No snapshots loaded.
final class AnnotationHistoryInitial extends AnnotationHistoryState {
  const AnnotationHistoryInitial();

  @override
  List<Object?> get props => [];
}

/// Snapshots loaded for a script.
final class AnnotationHistoryLoaded extends AnnotationHistoryState {
  const AnnotationHistoryLoaded({
    required this.scriptId,
    required this.snapshots,
  });

  final String scriptId;
  final List<AnnotationSnapshot> snapshots;

  @override
  List<Object?> get props => [scriptId, snapshots];
}
```

- [ ] **Step 3: Create cubit**

Create `horatio_app/lib/bloc/annotation/annotation_history_cubit.dart`:

```dart
import 'dart:async';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/annotation/annotation_history_state.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:uuid/uuid.dart';

/// Manages annotation snapshot history for a script.
class AnnotationHistoryCubit extends Cubit<AnnotationHistoryState> {
  /// Creates an [AnnotationHistoryCubit].
  AnnotationHistoryCubit({required AnnotationDao dao})
      : _dao = dao,
        super(const AnnotationHistoryInitial());

  final AnnotationDao _dao;
  StreamSubscription<List<AnnotationSnapshot>>? _sub;
  String? _scriptId;

  static const _uuid = Uuid();

  /// Subscribes to snapshots for a script.
  void loadSnapshots(String scriptId) {
    _scriptId = scriptId;
    _sub?.cancel();
    _sub = _dao.watchSnapshotsForScript(scriptId).listen((snapshots) {
      emit(AnnotationHistoryLoaded(
        scriptId: scriptId,
        snapshots: snapshots,
      ));
    });
  }

  /// Saves current annotations as a snapshot.
  Future<void> saveSnapshot({
    required List<TextMark> marks,
    required List<LineNote> notes,
  }) async {
    final scriptId = _scriptId;
    if (scriptId == null) return;
    final snapshot = AnnotationSnapshot(
      id: _uuid.v4(),
      scriptId: scriptId,
      timestamp: DateTime.now().toUtc(),
      marks: marks,
      notes: notes,
    );
    await _dao.insertSnapshot(snapshot);
  }

  /// Restores annotations from a snapshot (destructive replace).
  Future<void> restoreSnapshot(AnnotationSnapshot snapshot) async {
    final scriptId = _scriptId;
    if (scriptId == null) return;
    await _dao.replaceAllAnnotations(
      scriptId: scriptId,
      marks: snapshot.marks,
      notes: snapshot.notes,
    );
  }

  @override
  Future<void> close() {
    _sub?.cancel();
    return super.close();
  }
}
```

- [ ] **Step 4: Run tests**

```bash
cd horatio_app && flutter test test/bloc/annotation_history_cubit_test.dart -v
```

- [ ] **Step 5: Commit**

```bash
git add horatio_app/lib/bloc/annotation/ \
        horatio_app/test/bloc/annotation_history_cubit_test.dart
git commit -m "feat(app): add AnnotationHistoryCubit for snapshot management"
```

---

## Chunk 4: Wiring + Build Pipeline

### Task 13: Wire database and cubits into app

**Files:**

- Modify: `horatio_app/lib/main.dart`
- Modify: `horatio_app/lib/app.dart`
- Modify: `horatio_app/test/app_test.dart`
- Modify: `horatio_app/test/widget_test.dart` (if present)
- Modify: any screen tests that call `pumpWidget(HoratioApp(...))`

- [ ] **Step 1: Initialize database in main.dart**

Replace `horatio_app/lib/main.dart` with:

```dart
import 'dart:io';

import 'package:device_preview/device_preview.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:horatio_app/app.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final dbFolder = await getApplicationDocumentsDirectory();
  final dbFile = File(p.join(dbFolder.path, 'horatio.sqlite'));
  final database = AppDatabase(NativeDatabase(dbFile));

  runApp(
    DevicePreview(
      builder: (_) => HoratioApp(database: database),
    ),
  );
}
```

- [ ] **Step 2: Update app.dart to accept database and provide AnnotationDao**

Replace `horatio_app/lib/app.dart` with:

```dart
import 'package:device_preview/device_preview.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/script_import/script_import_cubit.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_cubit.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_app/services/script_repository.dart';
import 'package:horatio_app/theme/app_theme.dart';

/// Root widget for the Horatio app.
class HoratioApp extends StatelessWidget {
  /// Creates the [HoratioApp].
  const HoratioApp({required this.database, super.key});

  /// The drift database instance.
  final AppDatabase database;

  @override
  Widget build(BuildContext context) => MultiRepositoryProvider(
        providers: [
          RepositoryProvider<ScriptRepository>(
            create: (_) => ScriptRepository(),
          ),
          RepositoryProvider<AnnotationDao>(
            create: (_) => database.annotationDao,
          ),
        ],
        child: MultiBlocProvider(
          providers: [
            BlocProvider<ScriptImportCubit>(
              create: (context) => ScriptImportCubit(
                repository: context.read<ScriptRepository>(),
              ),
            ),
            BlocProvider<SrsReviewCubit>(
              create: (_) => SrsReviewCubit(),
            ),
          ],
          child: MaterialApp.router(
            title: 'Horatio',
            theme: AppTheme.light,
            darkTheme: AppTheme.dark,
            locale: DevicePreview.locale(context),
            builder: DevicePreview.appBuilder,
            routerConfig: appRouter,
          ),
        ),
      );
}
```

Note: `HoratioApp` is no longer `const`-constructible because `AppDatabase`
is not const. All call sites must be updated.

- [ ] **Step 3: Create test helper for in-memory database**

Create `horatio_app/test/helpers/test_database.dart`:

```dart
import 'package:drift/native.dart';
import 'package:horatio_app/database/app_database.dart';

/// Creates an in-memory [AppDatabase] for tests.
AppDatabase createTestDatabase() => AppDatabase(NativeDatabase.memory());
```

- [ ] **Step 4: Update app_test.dart**

Replace all `const HoratioApp()` with `HoratioApp(database: createTestDatabase())`:

```dart
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/app.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_core/horatio_core.dart';

import 'helpers/test_database.dart';

void main() {
  testWidgets('HoratioApp builds without crashing', (tester) async {
    await tester.pumpWidget(HoratioApp(database: createTestDatabase()));
    await tester.pumpAndSettle();
    expect(find.text('Horatio'), findsOneWidget);
  });

  testWidgets('SrsReviewCubit is created when srs-review route is visited',
      (tester) async {
    await tester.pumpWidget(HoratioApp(database: createTestDatabase()));
    await tester.pumpAndSettle();

    unawaited(appRouter.push(RoutePaths.srsReview, extra: <SrsCard>[
      SrsCard(id: 'c1', cueText: 'Cue', answerText: 'Ans'),
    ]));
    await tester.pumpAndSettle();
    expect(find.text('No review session active.'), findsOneWidget);
  });
}
```

- [ ] **Step 5: Search and update all other test files that create HoratioApp**

```bash
grep -rn 'HoratioApp()' horatio_app/test/
grep -rn 'const HoratioApp' horatio_app/test/
```

Update every occurrence to use `HoratioApp(database: createTestDatabase())`
and add the test_database import.

- [ ] **Step 6: Run all app tests**

```bash
cd horatio_app && flutter test
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add horatio_app/lib/main.dart horatio_app/lib/app.dart \
        horatio_app/test/
git commit -m "feat(app): wire drift database and AnnotationDao into app"
```

---

### Task 14: Add build_runner step to run.sh

**Files:**

- Modify: `horatio/run.sh`

- [ ] **Step 1: Add app_codegen function**

Add this function after `app_get()` in the "App tasks" section of `run.sh`:

```bash
app_codegen() {
    local h
    h=$(files_hash "$APP_DIR/lib/database" -name '*.dart' ! -name '*.g.dart')
    if step_cached app_codegen "$h"; then
        echo "  [cached] app_codegen — skipping"
        return
    fi
    heading "Running drift codegen"
    cd "$APP_DIR"
    dart run build_runner build --delete-conflicting-outputs
    cache_step app_codegen "$h"
}
```

- [ ] **Step 2: Insert app_codegen into ALL pipeline functions that need .g.dart files**

Codegen must run before `app_analyze`, `app_test`, `app_build`, and `do_dead_code`.
Insert `app_codegen` right after `app_get` in each of these pipelines:

```bash
do_analyze() {
    check_deps
    core_get
    core_format
    core_analyze
    ensure_flutter
    app_get
    app_codegen          # NEW — before dead_code (scans .dart files)
    do_dead_code
}

do_test() {
    check_deps
    core_get
    core_test
    ensure_flutter
    app_get
    app_codegen          # NEW — before app_test
    app_test
}

do_run() {
    check_deps
    ensure_flutter
    ensure_whisper
    core_get
    app_get
    app_codegen          # NEW — before app_analyze and app_build
    app_analyze
    app_build
    app_run
}

do_web() {
    check_deps
    ensure_flutter
    ensure_whisper
    core_get
    app_get
    app_codegen          # NEW — before app_analyze
    app_analyze
    app_web
}
```

- [ ] **Step 3: Test the run.sh change**

```bash
cd horatio && bash run.sh test
```

Expected: codegen runs, then tests pass.

- [ ] **Step 4: Commit**

```bash
git add horatio/run.sh
git commit -m "chore: add drift codegen step to run.sh with caching"
```

---

### Task 15: Run full pipeline and verify coverage

- [ ] **Step 1: Run full test + analyze pipeline**

```bash
cd horatio && bash run.sh -f test
cd horatio && bash run.sh -f analyze
```

Expected: all analysis clean, all tests pass, 100% coverage on both packages.

- [ ] **Step 2: Run pre-commit**

```bash
pre-commit run --files $(git diff --name-only HEAD~10)
```

Fix any issues found.

- [ ] **Step 3: Final commit and push**

```bash
git add -A
git commit -m "feat: annotations subsystem — core models, drift DB, cubits"
git push
```

---

## Chunk 5: UI (Annotation Editor Screen)

> The UI tasks are deliberately less granular since widget code depends heavily
> on visual feedback during development. Each task below should be broken into
> finer TDD steps at implementation time.
>
> **Required branch coverage scenarios** (I5): Every widget test must cover
> these branch scenarios to maintain 100% coverage.
>
> **Deferred:** Showing marks/note badges during rehearsal (spec §UI Components)
> will be a follow-up task after the annotation editor is complete.

### Task 16: Add annotation routes

**Files:**

- Modify: `horatio_app/lib/router.dart`

Add routes for `/annotations` and `/annotation-history`. Both take
`extra: {'script': Script}`.

**Branch tests:** Route resolves correctly, route with null extra shows error.

---

### Task 17: Create mark overlay widget

**Files:**

- Create: `horatio_app/lib/widgets/mark_overlay.dart`
- Create: `horatio_app/test/widgets/mark_overlay_test.dart`

A widget that renders colored highlights on a `Text` widget based on a
`List<TextMark>`. Each `MarkType` gets a distinct color.

**Branch tests:**

- Empty marks list renders plain text
- Single mark renders colored span
- Multiple overlapping marks render correctly
- Each `MarkType` maps to a distinct color (iterate all values)
- Mark outside text bounds is handled gracefully

---

### Task 18: Create note indicator widget

**Files:**

- Create: `horatio_app/lib/widgets/note_indicator.dart`
- Create: `horatio_app/test/widgets/note_indicator_test.dart`

A small icon badge showing count of notes on a line. Tappable to expand.

**Branch tests:**

- Zero notes: indicator hidden
- One note: shows "1" badge
- Multiple notes: shows count badge
- Tap triggers callback

---

### Task 19: Create mark type picker widget

**Files:**

- Create: `horatio_app/lib/widgets/mark_type_picker.dart`
- Create: `horatio_app/test/widgets/mark_type_picker_test.dart`

Popup with `MarkType` options shown after user selects a text span.

**Branch tests:**

- All 6 `MarkType` values displayed
- Tap on each type calls onSelected with correct type
- Dismissing without selection calls onCancelled

---

### Task 20: Create note editor bottom sheet

**Files:**

- Create: `horatio_app/lib/widgets/note_editor_sheet.dart`
- Create: `horatio_app/test/widgets/note_editor_sheet_test.dart`

Bottom sheet with category picker and text field, shown on long-press of a line.

**Branch tests:**

- All 6 `NoteCategory` values in picker
- Submit with text calls onSave
- Submit with empty text is disabled / shows validation
- Cancel dismisses sheet
- Pre-filled text when editing existing note

---

### Task 21: Create annotation editor screen

**Files:**

- Create: `horatio_app/lib/screens/annotation_editor_screen.dart`
- Create: `horatio_app/test/screens/annotation_editor_screen_test.dart`

Full editor screen composing the widgets above, wired to both cubits.

**Branch tests:**

- Renders lines with marks overlay
- Renders note indicators on lines with notes
- Text selection shows mark type picker
- Long-press shows note editor sheet
- Line tap emits `selectLine`
- AnnotationInitial state shows loading indicator
- AnnotationLoaded state shows script lines

---

### Task 22: Create annotation history screen

**Files:**

- Create: `horatio_app/lib/screens/annotation_history_screen.dart`
- Create: `horatio_app/test/screens/annotation_history_screen_test.dart`

Timeline list of snapshots with restore buttons (confirmation dialog).

**Branch tests:**

- Empty snapshot list shows "No history yet" message
- Snapshots rendered with timestamp and mark/note counts
- Restore button shows confirmation dialog
- Confirm restore calls `restoreSnapshot` on cubit
- Cancel restore dismisses dialog
- Save snapshot button calls `saveSnapshot`

---

### Task 23: Add annotation entry point to role selection

**Files:**

- Modify: `horatio_app/lib/screens/role_selection_screen.dart`

Add an "Annotate Script" option to the bottom sheet in `_navigateWithRole`.

**Branch tests:**

- "Annotate Script" option visible
- Tap navigates to annotation editor route

---

### Task 24: Final integration test + coverage

- [ ] **Step 1: Run full pipeline**

```bash
cd horatio && bash run.sh -f full
```

- [ ] **Step 2: Run pre-commit on all changed files**

```bash
pre-commit run --all-files
```

- [ ] **Step 3: Commit and push**

```bash
git add -A
git commit -m "feat: annotation editor and history UI screens"
git push
```
