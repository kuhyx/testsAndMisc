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
