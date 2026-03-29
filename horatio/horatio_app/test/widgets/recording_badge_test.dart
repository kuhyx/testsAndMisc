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
