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
      expect(
        find.textContaining('This is a very long note that '),
        findsOneWidget,
      );
      expect(find.byIcon(Icons.psychology), findsOneWidget);
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
