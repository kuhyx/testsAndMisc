import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/note_editor_sheet.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  group('NoteEditorSheet', () {
    testWidgets('displays all 6 NoteCategory values in dropdown',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteEditorSheet(onSave: (_, __) {}, onCancel: () {}),
          ),
        ),
      );

      // Open the dropdown.
      await tester.tap(find.byType(DropdownButtonFormField<NoteCategory>));
      await tester.pumpAndSettle();

      for (final category in NoteCategory.values) {
        expect(
          find.text(noteCategoryLabel(category)),
          findsWidgets,
          reason: '${category.name} should appear in dropdown',
        );
      }
    });

    testWidgets('submit with text calls onSave', (tester) async {
      NoteCategory? savedCategory;
      String? savedText;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteEditorSheet(
              onSave: (category, text) {
                savedCategory = category;
                savedText = text;
              },
              onCancel: () {},
            ),
          ),
        ),
      );

      await tester.enterText(find.byType(TextFormField), 'My note');
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      expect(savedCategory, NoteCategory.general);
      expect(savedText, 'My note');
    });

    testWidgets('submit with empty text shows validation error',
        (tester) async {
      var saveCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteEditorSheet(
              onSave: (_, __) => saveCalled = true,
              onCancel: () {},
            ),
          ),
        ),
      );

      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      expect(find.text('Note cannot be empty'), findsOneWidget);
      expect(saveCalled, isFalse);
    });

    testWidgets('cancel calls onCancel', (tester) async {
      var cancelled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteEditorSheet(
              onSave: (_, __) {},
              onCancel: () => cancelled = true,
            ),
          ),
        ),
      );

      await tester.tap(find.text('Cancel'));
      expect(cancelled, isTrue);
    });

    testWidgets('pre-filled initialText and initialCategory', (tester) async {
      NoteCategory? savedCategory;
      String? savedText;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteEditorSheet(
              onSave: (category, text) {
                savedCategory = category;
                savedText = text;
              },
              onCancel: () {},
              initialCategory: NoteCategory.emotion,
              initialText: 'Existing note',
            ),
          ),
        ),
      );

      // Verify text is pre-filled.
      expect(find.text('Existing note'), findsOneWidget);

      // Verify category label shown (the selected value).
      expect(find.text('Emotion'), findsOneWidget);

      // Submit without changes.
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      expect(savedCategory, NoteCategory.emotion);
      expect(savedText, 'Existing note');
    });

    testWidgets('changing category updates selection', (tester) async {
      NoteCategory? savedCategory;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteEditorSheet(
              onSave: (category, _) => savedCategory = category,
              onCancel: () {},
            ),
          ),
        ),
      );

      // Open dropdown and select "Intention".
      await tester.tap(find.byType(DropdownButtonFormField<NoteCategory>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Intention').last);
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), 'Test');
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      expect(savedCategory, NoteCategory.intention);
    });
  });
}
