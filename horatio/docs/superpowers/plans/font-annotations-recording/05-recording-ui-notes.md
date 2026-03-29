## Chunk 5: Recording UI + Note UX Improvements

### Task 5.1: GradeStars widget

**Files:**

- Create: `horatio_app/lib/widgets/grade_stars.dart`
- Create: `horatio_app/test/widgets/grade_stars_test.dart`

- [ ] **Step 1: Write failing tests**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/grade_stars.dart';

void main() {
  group('GradeStars', () {
    testWidgets('shows 5 star icons and blackout button', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: null, onGrade: (_) {}),
          ),
        ),
      );
      expect(find.byIcon(Icons.star_border), findsNWidgets(5));
      expect(find.text('Blackout'), findsOneWidget);
    });

    testWidgets('filled stars match grade', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: 3, onGrade: (_) {}),
          ),
        ),
      );
      expect(find.byIcon(Icons.star), findsNWidgets(3));
      expect(find.byIcon(Icons.star_border), findsNWidgets(2));
    });

    testWidgets('tapping star calls onGrade', (tester) async {
      int? graded;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: null, onGrade: (g) => graded = g),
          ),
        ),
      );
      // Tap the 4th star (index 3, value 4).
      await tester.tap(find.byIcon(Icons.star_border).at(3));
      expect(graded, 4);
    });

    testWidgets('tapping blackout calls onGrade with 0', (tester) async {
      int? graded;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: null, onGrade: (g) => graded = g),
          ),
        ),
      );
      await tester.tap(find.text('Blackout'));
      expect(graded, 0);
    });

    testWidgets('grade 0 highlights blackout button', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: 0, onGrade: (_) {}),
          ),
        ),
      );
      // All stars empty when grade is 0.
      expect(find.byIcon(Icons.star_border), findsNWidgets(5));
    });

    testWidgets('grade 5 fills all stars', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: 5, onGrade: (_) {}),
          ),
        ),
      );
      expect(find.byIcon(Icons.star), findsNWidgets(5));
      expect(find.byIcon(Icons.star_border), findsNothing);
    });
  });
}
```

- [ ] **Step 2: Implement GradeStars**

```dart
import 'package:flutter/material.dart';

/// A 0–5 grade widget with tappable stars and a "Blackout" (grade 0) button.
class GradeStars extends StatelessWidget {
  /// Creates a [GradeStars].
  const GradeStars({
    required this.grade,
    required this.onGrade,
    super.key,
  });

  /// Current grade (0-5), null if not yet graded.
  final int? grade;

  /// Called with the selected grade (0-5).
  final ValueChanged<int> onGrade;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextButton(
            onPressed: () => onGrade(0),
            style: TextButton.styleFrom(
              foregroundColor:
                  grade == 0 ? Colors.red : null,
            ),
            child: const Text('Blackout'),
          ),
          for (var i = 1; i <= 5; i++)
            IconButton(
              icon: Icon(
                grade != null && i <= grade! ? Icons.star : Icons.star_border,
                color: Colors.amber,
              ),
              onPressed: () => onGrade(i),
            ),
        ],
      );
}
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/widgets/grade_stars_test.dart -v
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/widgets/grade_stars.dart horatio_app/test/widgets/grade_stars_test.dart
git commit -m "feat(recording): add GradeStars widget"
```

---

### Task 5.2: RecordingBadge widget

**Files:**

- Create: `horatio_app/lib/widgets/recording_badge.dart`
- Create: `horatio_app/test/widgets/recording_badge_test.dart`

- [ ] **Step 1: Write failing tests**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/recording_badge.dart';

void main() {
  group('RecordingBadge', () {
    testWidgets('hidden when count is 0', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingBadge(recordingCount: 0, onTap: () {}),
          ),
        ),
      );
      expect(find.byType(SizedBox), findsOneWidget);
      expect(find.byIcon(Icons.mic), findsNothing);
    });

    testWidgets('shows mic icon and count', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingBadge(recordingCount: 3, onTap: () {}),
          ),
        ),
      );
      expect(find.byIcon(Icons.mic), findsOneWidget);
      expect(find.text('3'), findsOneWidget);
    });

    testWidgets('tap calls onTap', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingBadge(
              recordingCount: 1,
              onTap: () => tapped = true,
            ),
          ),
        ),
      );
      await tester.tap(find.byIcon(Icons.mic));
      expect(tapped, isTrue);
    });
  });
}
```

- [ ] **Step 2: Implement RecordingBadge**

```dart
import 'package:flutter/material.dart';

/// A small mic icon with count badge, showing recordings per line.
class RecordingBadge extends StatelessWidget {
  /// Creates a [RecordingBadge].
  const RecordingBadge({
    required this.recordingCount,
    required this.onTap,
    super.key,
  });

  /// Number of recordings for the line.
  final int recordingCount;

  /// Callback when tapped.
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    if (recordingCount == 0) return const SizedBox.shrink();
    return GestureDetector(
      onTap: onTap,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.mic, size: 16),
          const SizedBox(width: 2),
          Text(
            '$recordingCount',
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/widgets/recording_badge_test.dart -v
```

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/widgets/recording_badge.dart horatio_app/test/widgets/recording_badge_test.dart
git commit -m "feat(recording): add RecordingBadge widget"
```

---

### Task 5.3: RecordingActionBar widget

**Files:**

- Create: `horatio_app/lib/widgets/recording_action_bar.dart`
- Create: `horatio_app/test/widgets/recording_action_bar_test.dart`

- [ ] **Step 1: Write failing tests**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/recording_action_bar.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  group('RecordingActionBar', () {
    testWidgets('shows record button', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingActionBar(
              isRecording: false,
              elapsed: Duration.zero,
              latestRecording: null,
              onRecord: () {},
              onStop: () {},
              onPlay: () {},
            ),
          ),
        ),
      );
      expect(find.byIcon(Icons.mic), findsOneWidget);
    });

    testWidgets('shows stop button when recording', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingActionBar(
              isRecording: true,
              elapsed: const Duration(seconds: 5),
              latestRecording: null,
              onRecord: () {},
              onStop: () {},
              onPlay: () {},
            ),
          ),
        ),
      );
      expect(find.byIcon(Icons.stop), findsOneWidget);
      expect(find.textContaining('0:05'), findsOneWidget);
    });

    testWidgets('play button enabled when recording exists', (tester) async {
      final recording = LineRecording(
        id: 'r1',
        scriptId: 's1',
        lineIndex: 0,
        filePath: '/p.m4a',
        durationMs: 3000,
        createdAt: DateTime.utc(2026),
      );
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingActionBar(
              isRecording: false,
              elapsed: Duration.zero,
              latestRecording: recording,
              onRecord: () {},
              onStop: () {},
              onPlay: () {},
            ),
          ),
        ),
      );
      expect(find.byIcon(Icons.play_arrow), findsOneWidget);
    });

    testWidgets('play button disabled when no recording', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingActionBar(
              isRecording: false,
              elapsed: Duration.zero,
              latestRecording: null,
              onRecord: () {},
              onStop: () {},
              onPlay: () {},
            ),
          ),
        ),
      );
      final playButton = tester.widget<IconButton>(
        find.widgetWithIcon(IconButton, Icons.play_arrow),
      );
      expect(playButton.onPressed, isNull);
    });

    testWidgets('tap record calls onRecord', (tester) async {
      var called = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingActionBar(
              isRecording: false,
              elapsed: Duration.zero,
              latestRecording: null,
              onRecord: () => called = true,
              onStop: () {},
              onPlay: () {},
            ),
          ),
        ),
      );
      await tester.tap(find.byIcon(Icons.mic));
      expect(called, isTrue);
    });

    testWidgets('tap stop calls onStop', (tester) async {
      var called = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingActionBar(
              isRecording: true,
              elapsed: Duration.zero,
              latestRecording: null,
              onRecord: () {},
              onStop: () => called = true,
              onPlay: () {},
            ),
          ),
        ),
      );
      await tester.tap(find.byIcon(Icons.stop));
      expect(called, isTrue);
    });
  });
}
```

- [ ] **Step 2: Implement RecordingActionBar**

```dart
import 'package:flutter/material.dart';
import 'package:horatio_core/horatio_core.dart';

/// Bottom action bar for record/play controls on a selected line.
class RecordingActionBar extends StatelessWidget {
  /// Creates a [RecordingActionBar].
  const RecordingActionBar({
    required this.isRecording,
    required this.elapsed,
    required this.latestRecording,
    required this.onRecord,
    required this.onStop,
    required this.onPlay,
    super.key,
  });

  /// Whether currently recording.
  final bool isRecording;

  /// Elapsed recording time.
  final Duration elapsed;

  /// Most recent recording for the selected line (null if none).
  final LineRecording? latestRecording;

  /// Start recording callback.
  final VoidCallback onRecord;

  /// Stop recording callback.
  final VoidCallback onStop;

  /// Play last recording callback.
  final VoidCallback onPlay;

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes;
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          border: Border(
            top: BorderSide(
              color: Theme.of(context).colorScheme.outline.withValues(
                    alpha: 0.3,
                  ),
            ),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isRecording) ...[
              IconButton(
                icon: const Icon(Icons.stop, color: Colors.red),
                onPressed: onStop,
                tooltip: 'Stop Recording',
              ),
              Text(_formatDuration(elapsed)),
            ] else ...[
              IconButton(
                icon: const Icon(Icons.mic),
                onPressed: onRecord,
                tooltip: 'Record',
              ),
            ],
            const SizedBox(width: 16),
            IconButton(
              icon: const Icon(Icons.play_arrow),
              onPressed: latestRecording != null ? onPlay : null,
              tooltip: 'Play Last Recording',
            ),
          ],
        ),
      );
}
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/widgets/recording_action_bar_test.dart -v
```

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/widgets/recording_action_bar.dart horatio_app/test/widgets/recording_action_bar_test.dart
git commit -m "feat(recording): add RecordingActionBar widget"
```

---

### Task 5.4: RecordingListSheet widget

**Files:**

- Create: `horatio_app/lib/widgets/recording_list_sheet.dart`
- Create: `horatio_app/test/widgets/recording_list_sheet_test.dart`

- [ ] **Step 1: Write failing tests**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/recording_list_sheet.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  final recordings = [
    LineRecording(
      id: 'r1',
      scriptId: 's1',
      lineIndex: 0,
      filePath: '/p1.m4a',
      durationMs: 5000,
      createdAt: DateTime.utc(2026),
      grade: 3,
    ),
    LineRecording(
      id: 'r2',
      scriptId: 's1',
      lineIndex: 0,
      filePath: '/p2.m4a',
      durationMs: 3000,
      createdAt: DateTime.utc(2026, 1, 2),
    ),
  ];

  group('RecordingListSheet', () {
    testWidgets('shows recordings', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingListSheet(
              recordings: recordings,
              onPlay: (_) {},
              onDelete: (_) {},
            ),
          ),
        ),
      );
      expect(find.textContaining('5.0s'), findsOneWidget);
      expect(find.textContaining('3.0s'), findsOneWidget);
    });

    testWidgets('shows empty message', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingListSheet(
              recordings: const [],
              onPlay: (_) {},
              onDelete: (_) {},
            ),
          ),
        ),
      );
      expect(find.text('No recordings'), findsOneWidget);
    });

    testWidgets('tap play calls onPlay', (tester) async {
      LineRecording? played;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingListSheet(
              recordings: recordings,
              onPlay: (r) => played = r,
              onDelete: (_) {},
            ),
          ),
        ),
      );
      await tester.tap(find.byIcon(Icons.play_arrow).first);
      expect(played?.id, 'r1');
    });

    testWidgets('tap delete calls onDelete', (tester) async {
      String? deleted;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingListSheet(
              recordings: recordings,
              onPlay: (_) {},
              onDelete: (id) => deleted = id,
            ),
          ),
        ),
      );
      await tester.tap(find.byIcon(Icons.delete).first);
      expect(deleted, 'r1');
    });

    testWidgets('shows grade for graded recording', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingListSheet(
              recordings: recordings,
              onPlay: (_) {},
              onDelete: (_) {},
            ),
          ),
        ),
      );
      // First recording has grade 3.
      expect(find.byIcon(Icons.star), findsWidgets);
    });
  });
}
```

- [ ] **Step 2: Implement RecordingListSheet**

```dart
import 'package:flutter/material.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:intl/intl.dart';

/// Bottom sheet listing all recordings for a line.
class RecordingListSheet extends StatelessWidget {
  /// Creates a [RecordingListSheet].
  const RecordingListSheet({
    required this.recordings,
    required this.onPlay,
    required this.onDelete,
    super.key,
  });

  /// Recordings to display.
  final List<LineRecording> recordings;

  /// Called when play is tapped for a recording.
  final ValueChanged<LineRecording> onPlay;

  /// Called when delete is tapped for a recording.
  final ValueChanged<String> onDelete;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Recordings',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            if (recordings.isEmpty)
              const Center(child: Text('No recordings'))
            else
              ...recordings.map(
                (r) => ListTile(
                  leading: IconButton(
                    icon: const Icon(Icons.play_arrow),
                    onPressed: () => onPlay(r),
                  ),
                  title: Text(
                    '${(r.durationMs / 1000).toStringAsFixed(1)}s — '
                    '${DateFormat.yMd().format(r.createdAt)}',
                  ),
                  subtitle: r.grade != null
                      ? Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            for (var i = 0; i < r.grade!; i++)
                              const Icon(Icons.star,
                                  size: 14, color: Colors.amber),
                          ],
                        )
                      : const Text('Not graded'),
                  trailing: IconButton(
                    icon: const Icon(Icons.delete),
                    onPressed: () => onDelete(r.id),
                  ),
                ),
              ),
          ],
        ),
      );
}
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/widgets/recording_list_sheet_test.dart -v
```

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/widgets/recording_list_sheet.dart horatio_app/test/widgets/recording_list_sheet_test.dart
git commit -m "feat(recording): add RecordingListSheet widget"
```

---

### Task 5.5: NoteChip widget

**Files:**

- Create: `horatio_app/lib/widgets/note_chip.dart`
- Create: `horatio_app/test/widgets/note_chip_test.dart`

- [ ] **Step 1: Write failing tests**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/note_chip.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  group('NoteChip', () {
    testWidgets('shows truncated text and category', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteChip(
              note: LineNote(
                id: 'n1',
                lineIndex: 0,
                category: NoteCategory.intention,
                text: 'This is a very long note that should be truncated',
                createdAt: DateTime.utc(2026),
              ),
              onTap: () {},
              onDelete: () {},
            ),
          ),
        ),
      );
      // Truncated to 30 chars.
      expect(find.textContaining('This is a very long note that '), findsOneWidget);
    });

    testWidgets('short text not truncated', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteChip(
              note: LineNote(
                id: 'n1',
                lineIndex: 0,
                category: NoteCategory.emotion,
                text: 'Short note',
                createdAt: DateTime.utc(2026),
              ),
              onTap: () {},
              onDelete: () {},
            ),
          ),
        ),
      );
      expect(find.text('Short note'), findsOneWidget);
    });

    testWidgets('tap calls onTap', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteChip(
              note: LineNote(
                id: 'n1',
                lineIndex: 0,
                category: NoteCategory.general,
                text: 'Test',
                createdAt: DateTime.utc(2026),
              ),
              onTap: () => tapped = true,
              onDelete: () {},
            ),
          ),
        ),
      );
      await tester.tap(find.byType(ActionChip));
      expect(tapped, isTrue);
    });

    testWidgets('long-press calls onDelete', (tester) async {
      var deleted = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteChip(
              note: LineNote(
                id: 'n1',
                lineIndex: 0,
                category: NoteCategory.blocking,
                text: 'Test',
                createdAt: DateTime.utc(2026),
              ),
              onTap: () {},
              onDelete: () => deleted = true,
            ),
          ),
        ),
      );
      await tester.longPress(find.byType(GestureDetector).first);
      expect(deleted, isTrue);
    });
  });
}
```

- [ ] **Step 2: Implement NoteChip**

```dart
import 'package:flutter/material.dart';
import 'package:horatio_core/horatio_core.dart';

/// Category icons for note chips.
const Map<NoteCategory, IconData> noteCategoryIcons = {
  NoteCategory.intention: Icons.psychology,
  NoteCategory.subtext: Icons.chat_bubble_outline,
  NoteCategory.blocking: Icons.directions_walk,
  NoteCategory.emotion: Icons.favorite,
  NoteCategory.delivery: Icons.record_voice_over,
  NoteCategory.general: Icons.note,
};

/// An inline chip displaying a note's category icon and truncated text.
class NoteChip extends StatelessWidget {
  /// Creates a [NoteChip].
  const NoteChip({
    required this.note,
    required this.onTap,
    required this.onDelete,
    super.key,
  });

  /// The note to display.
  final LineNote note;

  /// Called when the chip is tapped (edit).
  final VoidCallback onTap;

  /// Called when the chip is long-pressed (delete).
  final VoidCallback onDelete;

  String get _truncatedText =>
      note.text.length > 30 ? '${note.text.substring(0, 30)}…' : note.text;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onLongPress: onDelete,
        child: ActionChip(
          avatar: Icon(
            noteCategoryIcons[note.category] ?? Icons.note,
            size: 16,
          ),
          label: Text(_truncatedText),
          onPressed: onTap,
        ),
      );
}
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/widgets/note_chip_test.dart -v
```

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/widgets/note_chip.dart horatio_app/test/widgets/note_chip_test.dart
git commit -m "feat(notes): add NoteChip widget with category icon and truncation"
```

---

### Task 5.6: Update NoteEditorSheet for edit mode

**Files:**

- Modify: `horatio_app/lib/widgets/note_editor_sheet.dart`

- [ ] **Step 1: Add noteId parameter**

Change `onSave` callback type and add `noteId` parameter:

```dart
/// A bottom-sheet widget for creating or editing a [LineNote].
class NoteEditorSheet extends StatefulWidget {
  /// Creates a [NoteEditorSheet].
  const NoteEditorSheet({
    required this.onSave,
    required this.onCancel,
    this.initialCategory,
    this.initialText,
    this.noteId,
    super.key,
  });

  /// Called with the chosen category, text, and optional noteId on save.
  final void Function(NoteCategory category, String text, {String? noteId})
      onSave;

  /// Called when the user cancels editing.
  final VoidCallback onCancel;

  /// Pre-selected category when editing an existing note.
  final NoteCategory? initialCategory;

  /// Pre-filled text when editing an existing note.
  final String? initialText;

  /// Non-null when editing an existing note.
  final String? noteId;
```

Update `_submit` to pass `noteId`:

```dart
void _submit() {
  if (_formKey.currentState!.validate()) {
    widget.onSave(
      _category,
      _textController.text.trim(),
      noteId: widget.noteId,
    );
  }
}
```

- [ ] **Step 2: Update call sites and tests for new callback signature**

Update `_showNoteEditor` in `annotation_editor_screen.dart` (from Chunk 2) to use the new signature:

```dart
  void _showNoteEditor(BuildContext context) {
    final cubit = context.read<AnnotationCubit>();
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: NoteEditorSheet(
          onSave: (category, text, {String? noteId}) {
            cubit.addNote(
              lineIndex: widget.lineIndex,
              category: category,
              text: text,
            );
            Navigator.pop(context);
          },
          onCancel: () => Navigator.pop(context),
        ),
      ),
    );
  }
```

In all tests that use `NoteEditorSheet`, update `onSave` to accept the named `noteId` parameter:

```dart
onSave: (category, text, {String? noteId}) { ... },
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test
```

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/widgets/note_editor_sheet.dart horatio_app/test/
git commit -m "feat(notes): add noteId parameter to NoteEditorSheet for edit mode"
```

---

### Task 5.7: Update AnnotationDao + AnnotationCubit for note category updates

**Files:**

- Modify: `horatio_app/lib/database/daos/annotation_dao.dart`
- Modify: `horatio_app/lib/bloc/annotation/annotation_cubit.dart`
- Modify: `horatio_app/test/bloc/annotation_cubit_test.dart`

- [ ] **Step 1: Add updateNoteCategory to AnnotationDao**

Add this method to `AnnotationDao`:

```dart
/// Updates the category of a note.
Future<void> updateNoteCategory(String id, NoteCategory category) =>
    (update(lineNotesTable)..where((t) => t.id.equals(id)))
        .write(LineNotesTableCompanion(category: Value(category.name)));
```

- [ ] **Step 2: Update AnnotationCubit.updateNote**

Change signature to accept optional category:

```dart
/// Updates a note's text and/or category.
Future<void> updateNote(
  String id, {
  String? text,
  NoteCategory? category,
}) async {
  if (text != null) {
    await _dao.updateNoteText(id, text);
  }
  if (category != null) {
    await _dao.updateNoteCategory(id, category);
  }
}
```

- [ ] **Step 3: Update tests**

In `annotation_cubit_test.dart`, update the `updateNote` test and add a category update test:

```dart
test('updateNote calls dao.updateNoteText', () async {
  when(() => dao.updateNoteText('n1', 'new'))
      .thenAnswer((_) async {});
  final cubit = AnnotationCubit(dao: dao);
  await cubit.updateNote('n1', text: 'new');
  verify(() => dao.updateNoteText('n1', 'new')).called(1);
  await cubit.close();
});

test('updateNote calls dao.updateNoteCategory', () async {
  when(() => dao.updateNoteCategory('n1', NoteCategory.emotion))
      .thenAnswer((_) async {});
  final cubit = AnnotationCubit(dao: dao);
  await cubit.updateNote('n1', category: NoteCategory.emotion);
  verify(() => dao.updateNoteCategory('n1', NoteCategory.emotion)).called(1);
  await cubit.close();
});

test('updateNote with both text and category', () async {
  when(() => dao.updateNoteText('n1', 'new'))
      .thenAnswer((_) async {});
  when(() => dao.updateNoteCategory('n1', NoteCategory.blocking))
      .thenAnswer((_) async {});
  final cubit = AnnotationCubit(dao: dao);
  await cubit.updateNote('n1', text: 'new', category: NoteCategory.blocking);
  verify(() => dao.updateNoteText('n1', 'new')).called(1);
  verify(() => dao.updateNoteCategory('n1', NoteCategory.blocking)).called(1);
  await cubit.close();
});

test('updateNote with no arguments is no-op', () async {
  final cubit = AnnotationCubit(dao: dao);
  await cubit.updateNote('n1');
  verifyNever(() => dao.updateNoteText(any(), any()));
  verifyNever(() => dao.updateNoteCategory(any(), any()));
  await cubit.close();
});
```

- [ ] **Step 4: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/bloc/annotation_cubit_test.dart -v
```

- [ ] **Step 5: Commit**

```bash
git add horatio_app/lib/database/daos/annotation_dao.dart horatio_app/lib/bloc/annotation/annotation_cubit.dart horatio_app/test/bloc/annotation_cubit_test.dart
git commit -m "feat(notes): add updateNoteCategory to DAO and cubit"
```

---

### Task 5.8: Run pipeline for Chunk 5

- [ ] **Step 1: Run full pipeline**

```bash
cd /home/kuhy/testsAndMisc/horatio && ./run.sh test
```

Expected: 100% coverage.

---
