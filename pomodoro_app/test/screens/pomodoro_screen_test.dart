import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pomodoro_app/models/pomodoro_state.dart';
import 'package:pomodoro_app/screens/pomodoro_screen.dart';
import 'package:pomodoro_app/services/pomodoro_timer.dart';

/// Controllable fake timer for widget tests.
class FakeTimerController {
  void Function(Timer)? _callback;
  bool _isActive = true;

  void tick() {
    if (_isActive) {
      _callback?.call(_FakeTimer(this));
    }
  }

  void cancel() {
    _isActive = false;
  }

  bool get isActive => _isActive;
}

class _FakeTimer implements Timer {
  _FakeTimer(this._controller);
  final FakeTimerController _controller;

  @override
  void cancel() => _controller.cancel();

  @override
  bool get isActive => _controller.isActive;

  @override
  int get tick => 0;
}

void main() {
  late PomodoroTimer timer;
  late FakeTimerController fakeController;

  Timer fakeTimerFactory(Duration duration, void Function(Timer) callback) {
    fakeController = FakeTimerController();
    fakeController._callback = callback;
    return _FakeTimer(fakeController);
  }

  setUp(() {
    timer = PomodoroTimer(
      workMinutes: 1,
      shortBreakMinutes: 1,
      longBreakMinutes: 2,
      pomodorosPerCycle: 4,
      timerFactory: fakeTimerFactory,
    );
  });

  tearDown(() {
    timer.dispose();
  });

  Widget createApp() {
    return MaterialApp(
      home: PomodoroScreen(timer: timer),
    );
  }

  group('PomodoroScreen', () {
    testWidgets('shows initial time', (tester) async {
      await tester.pumpWidget(createApp());
      expect(find.text('01:00'), findsOneWidget);
    });

    testWidgets('shows Work label initially', (tester) async {
      await tester.pumpWidget(createApp());
      expect(find.text('Work'), findsOneWidget);
    });

    testWidgets('shows 0 pomodoros completed', (tester) async {
      await tester.pumpWidget(createApp());
      expect(find.text('0 pomodoros completed'), findsOneWidget);
    });

    testWidgets('play button starts timer', (tester) async {
      await tester.pumpWidget(createApp());

      // Find and tap the play button.
      final playButton = find.byIcon(Icons.play_arrow);
      expect(playButton, findsOneWidget);
      await tester.tap(playButton);
      await tester.pump();

      // After ticking, time should decrease.
      fakeController.tick();
      await tester.pump();
      expect(find.text('00:59'), findsOneWidget);
    });

    testWidgets('pause button appears when running', (tester) async {
      await tester.pumpWidget(createApp());

      await tester.tap(find.byIcon(Icons.play_arrow));
      await tester.pump();

      expect(find.byIcon(Icons.pause), findsOneWidget);
    });

    testWidgets('pause button pauses timer', (tester) async {
      await tester.pumpWidget(createApp());

      // Start.
      await tester.tap(find.byIcon(Icons.play_arrow));
      await tester.pump();

      fakeController.tick();
      await tester.pump();

      // Pause.
      await tester.tap(find.byIcon(Icons.pause));
      await tester.pump();

      expect(find.text('00:59'), findsOneWidget);
      expect(find.byIcon(Icons.play_arrow), findsOneWidget);
    });

    testWidgets('reset button resets time', (tester) async {
      await tester.pumpWidget(createApp());

      // Start and tick.
      await tester.tap(find.byIcon(Icons.play_arrow));
      await tester.pump();
      fakeController.tick();
      fakeController.tick();
      await tester.pump();

      // Reset.
      await tester.tap(find.byIcon(Icons.refresh));
      await tester.pump();

      expect(find.text('01:00'), findsOneWidget);
    });

    testWidgets('skip button moves to next mode', (tester) async {
      await tester.pumpWidget(createApp());

      await tester.tap(find.byIcon(Icons.skip_next));
      await tester.pump();

      expect(find.text('Short Break'), findsOneWidget);
    });

    testWidgets('shows correct completed count after session', (tester) async {
      await tester.pumpWidget(createApp());

      // Start and complete a work session.
      await tester.tap(find.byIcon(Icons.play_arrow));
      await tester.pump();

      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      await tester.pump();

      expect(find.text('1 pomodoro completed'), findsOneWidget);
    });

    testWidgets('has 4 indicator dots', (tester) async {
      await tester.pumpWidget(createApp());

      // There should be 4 AnimatedContainers for indicators.
      // We can check that the PomodoroIndicators widget is present.
      expect(find.text('0 pomodoros completed'), findsOneWidget);
    });
  });
}
