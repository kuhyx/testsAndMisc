import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/note_indicator.dart';

void main() {
  group('NoteIndicator', () {
    testWidgets('zero notes renders SizedBox.shrink', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: NoteIndicator(noteCount: 0, onTap: () {})),
        ),
      );

      expect(find.byType(SizedBox), findsOneWidget);
      expect(find.text('0'), findsNothing);
    });

    testWidgets('one note shows "1"', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: NoteIndicator(noteCount: 1, onTap: () {})),
        ),
      );

      expect(find.text('1'), findsOneWidget);
    });

    testWidgets('multiple notes shows count', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: NoteIndicator(noteCount: 5, onTap: () {})),
        ),
      );

      expect(find.text('5'), findsOneWidget);
    });

    testWidgets('tap triggers callback', (tester) async {
      var tapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NoteIndicator(noteCount: 3, onTap: () => tapped = true),
          ),
        ),
      );

      await tester.tap(find.text('3'));
      expect(tapped, isTrue);
    });
  });
}
