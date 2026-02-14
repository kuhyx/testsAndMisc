import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:pomodoro_app/models/pomodoro_state.dart';
import 'package:pomodoro_app/services/pomodoro_timer.dart';

/// A controllable fake timer for testing.
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
      workMinutes: 1, // 60 seconds for faster testing
      shortBreakMinutes: 1,
      longBreakMinutes: 2,
      pomodorosPerCycle: 2,
      timerFactory: fakeTimerFactory,
    );
  });

  tearDown(() {
    timer.dispose();
  });

  group('Initial state', () {
    test('starts in work mode', () {
      expect(timer.state.mode, PomodoroMode.work);
    });

    test('is not running', () {
      expect(timer.state.isRunning, false);
    });

    test('has correct initial time', () {
      expect(timer.state.remainingSeconds, 60);
      expect(timer.state.totalSeconds, 60);
    });

    test('has zero completed pomodoros', () {
      expect(timer.state.completedPomodoros, 0);
    });
  });

  group('start()', () {
    test('sets isRunning to true', () {
      timer.start();
      expect(timer.state.isRunning, true);
    });

    test('does nothing if already running', () {
      timer.start();
      final stateAfterFirstStart = timer.state;
      timer.start(); // second call
      expect(timer.state, stateAfterFirstStart);
    });

    test('notifies listeners', () {
      var notified = false;
      timer.addListener(() => notified = true);
      timer.start();
      expect(notified, true);
    });
  });

  group('pause()', () {
    test('sets isRunning to false', () {
      timer.start();
      timer.pause();
      expect(timer.state.isRunning, false);
    });

    test('does nothing if already paused', () {
      final state = timer.state;
      timer.pause();
      expect(timer.state, state);
    });

    test('preserves remaining time', () {
      timer.start();
      fakeController.tick(); // -1s
      fakeController.tick(); // -1s
      timer.pause();
      expect(timer.state.remainingSeconds, 58);
    });
  });

  group('Ticking', () {
    test('decrements remaining seconds', () {
      timer.start();
      fakeController.tick();
      expect(timer.state.remainingSeconds, 59);
    });

    test('notifies on each tick', () {
      timer.start();
      var count = 0;
      timer.addListener(() => count++);
      fakeController.tick();
      fakeController.tick();
      expect(count, 2);
    });
  });

  group('Session completion', () {
    test('transitions from work to short break', () {
      timer.start();
      // Tick down to 1 second, then one more tick completes.
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      expect(timer.state.mode, PomodoroMode.shortBreak);
      expect(timer.state.isRunning, false);
      expect(timer.state.completedPomodoros, 1);
    });

    test('transitions to long break after cycle', () {
      // Complete 2 pomodoros (pomodorosPerCycle = 2).
      // First pomodoro.
      timer.start();
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      expect(timer.state.mode, PomodoroMode.shortBreak);

      // Skip break.
      timer.skip();
      expect(timer.state.mode, PomodoroMode.work);

      // Second pomodoro.
      timer.start();
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      expect(timer.state.mode, PomodoroMode.longBreak);
      expect(timer.state.completedPomodoros, 2);
    });

    test('transitions from break to work', () {
      // Complete a work session.
      timer.start();
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      expect(timer.state.mode, PomodoroMode.shortBreak);

      // Complete the break.
      timer.start();
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      expect(timer.state.mode, PomodoroMode.work);
    });
  });

  group('reset()', () {
    test('resets to full duration', () {
      timer.start();
      fakeController.tick();
      fakeController.tick();
      timer.reset();
      expect(timer.state.remainingSeconds, 60);
      expect(timer.state.isRunning, false);
    });

    test('keeps the current mode', () {
      timer.start();
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      // Now in short break mode.
      timer.reset();
      expect(timer.state.mode, PomodoroMode.shortBreak);
    });
  });

  group('skip()', () {
    test('skips from work to short break', () {
      timer.skip();
      expect(timer.state.mode, PomodoroMode.shortBreak);
      expect(timer.state.isRunning, false);
    });

    test('skips from break to work', () {
      timer.skip(); // work -> short break
      timer.skip(); // short break -> work
      expect(timer.state.mode, PomodoroMode.work);
    });

    test('stops the timer when skipping', () {
      timer.start();
      timer.skip();
      expect(timer.state.isRunning, false);
    });
  });

  group('dispose()', () {
    test('cancels internal timer', () {
      // Create a separate timer so tearDown does not double-dispose.
      final disposableTimer = PomodoroTimer(
        workMinutes: 1,
        shortBreakMinutes: 1,
        longBreakMinutes: 2,
        pomodorosPerCycle: 2,
        timerFactory: fakeTimerFactory,
      );
      disposableTimer.start();
      disposableTimer.dispose();
      expect(fakeController.isActive, false);
    });
  });

  group('applyRemoteState()', () {
    test('applies remote state and notifies listeners', () {
      var notified = false;
      timer.addListener(() => notified = true);

      final remoteState = PomodoroState(
        mode: PomodoroMode.shortBreak,
        remainingSeconds: 200,
        totalSeconds: 300,
        isRunning: false,
        completedPomodoros: 2,
        pomodorosPerCycle: 4,
      );

      timer.applyRemoteState(remoteState, 'pause');
      expect(timer.state.mode, PomodoroMode.shortBreak);
      expect(timer.state.remainingSeconds, 200);
      expect(timer.state.completedPomodoros, 2);
      expect(timer.state.isRunning, false);
      expect(notified, true);
    });

    test('starts local ticking when remote state is running', () {
      final remoteState = PomodoroState(
        mode: PomodoroMode.work,
        remainingSeconds: 500,
        totalSeconds: 600,
        isRunning: true,
        completedPomodoros: 0,
        pomodorosPerCycle: 4,
      );

      timer.applyRemoteState(remoteState, 'start');
      expect(timer.state.isRunning, true);

      // The fake timer should have been created; ticking should work.
      fakeController.tick();
      expect(timer.state.remainingSeconds, 499);
    });

    test('stops local ticking when remote state is paused', () {
      // First start the timer locally.
      timer.start();
      fakeController.tick();
      expect(timer.state.remainingSeconds, 59);

      // Apply remote pause.
      final remoteState = timer.state.copyWith(isRunning: false);
      timer.applyRemoteState(remoteState, 'pause');
      expect(timer.state.isRunning, false);
    });
  });
}
