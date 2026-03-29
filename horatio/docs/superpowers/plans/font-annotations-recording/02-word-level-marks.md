## Chunk 2: Word-Level Mark Selection

### Task 2.1: MarkSelectionToolbar widget

**Files:**

- Create: `horatio_app/lib/widgets/mark_selection_toolbar.dart`
- Create: `horatio_app/test/widgets/mark_selection_toolbar_test.dart`

- [ ] **Step 1: Write failing tests**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/mark_selection_toolbar.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  group('MarkSelectionToolbar', () {
    testWidgets('shows 6 mark type chips', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MarkSelectionToolbar(
              onMarkSelected: (_) {},
              onCancelled: () {},
            ),
          ),
        ),
      );
      expect(find.byType(ActionChip), findsNWidgets(6));
      expect(find.text('Stress'), findsOneWidget);
      expect(find.text('Pause'), findsOneWidget);
      expect(find.text('Breath'), findsOneWidget);
      expect(find.text('Emphasis'), findsOneWidget);
      expect(find.text('Slow Down'), findsOneWidget);
      expect(find.text('Speed Up'), findsOneWidget);
    });

    testWidgets('tapping chip calls onMarkSelected', (tester) async {
      MarkType? selected;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MarkSelectionToolbar(
              onMarkSelected: (type) => selected = type,
              onCancelled: () {},
            ),
          ),
        ),
      );
      await tester.tap(find.text('Stress'));
      expect(selected, MarkType.stress);
    });

    testWidgets('cancel button calls onCancelled', (tester) async {
      var cancelled = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MarkSelectionToolbar(
              onMarkSelected: (_) {},
              onCancelled: () => cancelled = true,
            ),
          ),
        ),
      );
      await tester.tap(find.text('Cancel'));
      expect(cancelled, isTrue);
    });
  });
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/widgets/mark_selection_toolbar_test.dart
```

Expected: Compilation error — `MarkSelectionToolbar` does not exist.

- [ ] **Step 3: Implement MarkSelectionToolbar**

```dart
import 'package:flutter/material.dart';
import 'package:horatio_app/widgets/mark_overlay.dart';
import 'package:horatio_app/widgets/mark_type_picker.dart';
import 'package:horatio_core/horatio_core.dart';

/// Floating toolbar showing mark type chips for text selection annotation.
class MarkSelectionToolbar extends StatelessWidget {
  /// Creates a [MarkSelectionToolbar].
  const MarkSelectionToolbar({
    required this.onMarkSelected,
    required this.onCancelled,
    super.key,
  });

  /// Called when a mark type chip is tapped.
  final ValueChanged<MarkType> onMarkSelected;

  /// Called when the action is cancelled.
  final VoidCallback onCancelled;

  @override
  Widget build(BuildContext context) => Material(
        elevation: 4,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              ...MarkType.values.map(
                (type) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: ActionChip(
                    label: Text(markTypeLabel(type)),
                    backgroundColor: markColors[type],
                    onPressed: () => onMarkSelected(type),
                  ),
                ),
              ),
              const SizedBox(width: 4),
              TextButton(
                onPressed: onCancelled,
                child: const Text('Cancel'),
              ),
            ],
          ),
        ),
      );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/widgets/mark_selection_toolbar_test.dart -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add horatio_app/lib/widgets/mark_selection_toolbar.dart horatio_app/test/widgets/mark_selection_toolbar_test.dart
git commit -m "feat(marks): add MarkSelectionToolbar widget"
```

---

### Task 2.2: Rework \_LineTile for word-level selection

**Files:**

- Modify: `horatio_app/lib/screens/annotation_editor_screen.dart`
- Modify: `horatio_app/test/screens/annotation_editor_screen_test.dart`

- [ ] **Step 1: Replace \_LineTile implementation**

The `_LineTile` widget needs two distinct rendering modes:

**When `isSelected == false`**: Read-only `MarkOverlay` (current behavior minus long-press mark).

**When `isSelected == true`**: `SelectableText.rich` with colored spans + `MarkSelectionToolbar` appearing when text is selected.

Replace the `_LineTile` class with a `StatefulWidget` to manage the `TextSelection` and toolbar overlay:

```dart
class _LineTile extends StatefulWidget {
  const _LineTile({
    required this.line,
    required this.lineIndex,
    required this.marks,
    required this.notes,
    required this.isSelected,
  });

  final ScriptLine line;
  final int lineIndex;
  final List<TextMark> marks;
  final List<LineNote> notes;
  final bool isSelected;

  @override
  State<_LineTile> createState() => _LineTileState();
}

class _LineTileState extends State<_LineTile> {
  final LayerLink _layerLink = LayerLink();
  OverlayEntry? _toolbarOverlay;
  TextSelection? _selection;

  @override
  void dispose() {
    _removeToolbar();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant _LineTile oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!widget.isSelected && oldWidget.isSelected) {
      _removeToolbar();
    }
  }

  void _removeToolbar() {
    _toolbarOverlay?.remove();
    _toolbarOverlay = null;
  }

  void _onSelectionChanged(
    TextSelection selection,
    SelectionChangedCause? cause,
  ) {
    _removeToolbar();
    if (selection.isCollapsed) {
      _selection = null;
      return;
    }
    _selection = selection;
    _showToolbar();
  }

  void _showToolbar() {
    final overlay = Overlay.of(context);
    _toolbarOverlay = OverlayEntry(
      builder: (context) => Positioned(
        width: MediaQuery.of(context).size.width,
        child: CompositedTransformFollower(
          link: _layerLink,
          showWhenUnlinked: false,
          offset: const Offset(0, -48),
          child: Align(
            alignment: Alignment.centerLeft,
            child: MarkSelectionToolbar(
              onMarkSelected: _applyMark,
              onCancelled: _removeToolbar,
            ),
          ),
        ),
      ),
    );
    overlay.insert(_toolbarOverlay!);
  }

  void _applyMark(MarkType type) {
    final sel = _selection;
    if (sel == null || sel.isCollapsed) return;
    final start = sel.start;
    final end = sel.end;
    context.read<AnnotationCubit>().addMark(
          lineIndex: widget.lineIndex,
          startOffset: start,
          endOffset: end,
          type: type,
        );
    _removeToolbar();
  }

  List<TextSpan> _buildSpans() {
    // Reuse MarkOverlay's span-building logic but return TextSpan children.
    // (Could extract from MarkOverlay into a shared utility.)
    final text = widget.line.text;
    final marks = widget.marks;
    if (marks.isEmpty) return [TextSpan(text: text)];

    final length = text.length;
    final events = <({int offset, bool isStart, MarkType type})>[];
    for (final mark in marks) {
      final s = mark.startOffset.clamp(0, length);
      final e = mark.endOffset.clamp(0, length);
      if (s >= e) continue;
      events
        ..add((offset: s, isStart: true, type: mark.type))
        ..add((offset: e, isStart: false, type: mark.type));
    }
    events.sort((a, b) => a.offset.compareTo(b.offset));

    final spans = <TextSpan>[];
    var cursor = 0;
    final activeTypes = <MarkType>[];
    for (final event in events) {
      final pos = event.offset.clamp(0, length);
      if (pos > cursor) {
        spans.add(TextSpan(
          text: text.substring(cursor, pos),
          style: activeTypes.isEmpty
              ? null
              : TextStyle(backgroundColor: markColors[activeTypes.last]),
        ));
        cursor = pos;
      }
      if (event.isStart) {
        activeTypes.add(event.type);
      } else {
        activeTypes.remove(event.type);
      }
    }
    if (cursor < length) {
      spans.add(TextSpan(text: text.substring(cursor)));
    }
    return spans;
  }

  @override
  Widget build(BuildContext context) => Container(
        color: widget.isSelected
            ? Theme.of(context).colorScheme.primaryContainer.withValues(
                  alpha: 0.3,
                )
            : null,
        child: InkWell(
          onTap: () => context
              .read<AnnotationCubit>()
              .selectLine(widget.lineIndex),
          child: Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                Expanded(
                  child: widget.isSelected
                      ? CompositedTransformTarget(
                          link: _layerLink,
                          child: SelectableText.rich(
                            TextSpan(
                              style: DefaultTextStyle.of(context).style,
                              children: _buildSpans(),
                            ),
                            onSelectionChanged: _onSelectionChanged,
                          ),
                        )
                      : MarkOverlay(
                          text: widget.line.text,
                          marks: widget.marks,
                        ),
                ),
                NoteIndicator(
                  noteCount: widget.notes.length,
                  onTap: () => _showNoteEditor(context),
                ),
              ],
            ),
          ),
        ),
      );

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
          onSave: (category, text) {
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
}
```

> **Note:** `_showNoteEditor` uses the current `(NoteCategory, String)` callback. Task 5.6 will update this call site to the new `(NoteCategory, String, {String? noteId})` signature and add edit-mode support.

Remove the old `_showMarkPicker` method entirely (the long-press flow is replaced by text selection + toolbar).

- [ ] **Step 2: Update existing tests and add new ones**

Remove these three tests:

- `long-press on a line shows mark type picker`
- `selecting mark type in picker calls addMark`
- `cancel in mark picker dismisses dialog`

Add the following replacement tests:

```dart
testWidgets('selected line shows SelectableText', (tester) async {
  final script = _testScript();
  await tester.pumpWidget(_buildScreen(script));
  _marksCtrl.add([]);
  _notesCtrl.add([]);
  _snapshotsCtrl.add([]);
  await tester.pumpAndSettle();

  // Tap to select the first line.
  await tester.tap(
    find.text('To be or not to be.', findRichText: true),
  );
  await tester.pump();

  expect(find.byType(SelectableText), findsOneWidget);
});

testWidgets('unselected line shows MarkOverlay not SelectableText',
    (tester) async {
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

testWidgets('tapping a marked span shows remove dialog', (tester) async {
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
  await tester.tap(
    find.text('To be or not to be.', findRichText: true),
  );
  await tester.pump();

  // Tap the colored span area to trigger mark removal dialog.
  // The mark covers "To be" (offsets 0-5).
  await tester.tapAt(tester.getTopLeft(find.byType(SelectableText)));
  await tester.pump();

  expect(find.text('Remove mark?'), findsOneWidget);
});
```

Note: The overlay-based `MarkSelectionToolbar` is tested separately in `mark_selection_toolbar_test.dart`. The screen test verifies the mode transitions (selected → `SelectableText`, unselected → `MarkOverlay`). Full overlay interaction testing requires integration tests or the existing `MarkSelectionToolbar` widget tests.

- [ ] **Step 3: Add mark removal to \_LineTile**

When a line is selected and the user taps on a region that already has a mark (colored span), show an `AlertDialog` asking `'Remove mark?'` with Yes/No. On confirmation, call `cubit.removeMark(markId)`.

In `_LineTileState._buildSpans`, add a `TapGestureRecognizer` to colored spans:

```dart
if (activeTypes.isNotEmpty) {
  final markForSpan = marks.firstWhere(
    (m) =>
        m.startOffset <= cursor &&
        m.endOffset >= pos &&
        m.type == activeTypes.last,
  );
  spans.add(TextSpan(
    text: text.substring(cursor, pos),
    style: TextStyle(backgroundColor: markColors[activeTypes.last]),
    recognizer: TapGestureRecognizer()
      ..onTap = () => _showRemoveMarkDialog(markForSpan.id),
  ));
}
```

Add the `_showRemoveMarkDialog` method:

```dart
void _showRemoveMarkDialog(String markId) {
  showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Text('Remove mark?'),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(dialogContext),
          child: const Text('No'),
        ),
        TextButton(
          onPressed: () {
            context.read<AnnotationCubit>().removeMark(markId);
            Navigator.pop(dialogContext);
          },
          child: const Text('Yes'),
        ),
      ],
    ),
  );
}
```

Don't forget to import `TapGestureRecognizer` from `package:flutter/gestures.dart` and dispose recognizers properly.

- [ ] **Step 3: Run all tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/screens/annotation_editor_screen.dart horatio_app/test/screens/annotation_editor_screen_test.dart
git commit -m "feat(marks): replace whole-line marks with word-level text selection + toolbar"
```

---

### Task 2.3: Run full pipeline for Chunk 2

- [ ] **Step 1: Run codegen + analyze + test**

```bash
cd /home/kuhy/testsAndMisc/horatio && ./run.sh test
```

Expected: 100% coverage, all pass.

- [ ] **Step 2: Fix any issues**

---
