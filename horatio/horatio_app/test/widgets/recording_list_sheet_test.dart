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
              onGrade: (_, __) {},
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
              onGrade: (_, __) {},
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
              onGrade: (_, __) {},
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
              onGrade: (_, __) {},
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
              onGrade: (_, __) {},
              onDelete: (_) {},
            ),
          ),
        ),
      );
      expect(find.byIcon(Icons.star), findsWidgets);
    });

    testWidgets('tap grade calls onGrade', (tester) async {
      String? gradedId;
      int? gradedValue;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecordingListSheet(
              recordings: recordings,
              onPlay: (_) {},
              onGrade: (id, grade) {
                gradedId = id;
                gradedValue = grade;
              },
              onDelete: (_) {},
            ),
          ),
        ),
      );

      await tester.tap(find.text('Blackout').first);

      expect(gradedId, 'r1');
      expect(gradedValue, 0);
    });
  });
}
