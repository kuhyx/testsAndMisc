import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pomodoro_app/models/pomodoro_state.dart';
import 'package:pomodoro_app/services/notification_service.dart';
import 'package:pomodoro_app/services/pomodoro_timer.dart';
import 'package:pomodoro_app/services/sound_service.dart';

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
    fakeController = FakeTimerController()
      .._callback = callback;
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
      final stateAfterFirstStart = (timer..start()).state;
      timer.start(); // second call
      expect(timer.state, stateAfterFirstStart);
    });

    test('notifies listeners', () {
      var notified = false;
      timer
        ..addListener(() => notified = true)
        ..start();
      expect(notified, true);
    });
  });

  group('pause()', () {
    test('sets isRunning to false', () {
      timer
        ..start()
        ..pause();
      expect(timer.state.isRunning, false);
    });

    test('does nothing if already paused', () {
      final state = timer.state;
      timer.pause();
      expect(timer.state, state);
    });

    test('preserves remaining time', () {
      timer.start();
      fakeController
        ..tick() // -1s
        ..tick(); // -1s
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
      fakeController
        ..tick()
        ..tick();
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
      fakeController
        ..tick()
        ..tick();
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
      timer
        ..skip() // work -> short break
        ..skip(); // short break -> work
      expect(timer.state.mode, PomodoroMode.work);
    });

    test('stops the timer when skipping', () {
      timer
        ..start()
        ..skip();
      expect(timer.state.isRunning, false);
    });
  });

  group('dispose()', () {
    test('cancels internal timer', () {
      // Create a separate timer so tearDown does not double-dispose.
      PomodoroTimer(
        workMinutes: 1,
        shortBreakMinutes: 1,
        longBreakMinutes: 2,
        pomodorosPerCycle: 2,
        timerFactory: fakeTimerFactory,
      )
        ..start()
        ..dispose();
      expect(fakeController.isActive, false);
    });
  });

  group('switchStyle()', () {
    test('switches to ultraradian with correct durations', () {
      timer.switchStyle(TimerStyle.ultraradian);
      expect(timer.timerStyle, TimerStyle.ultraradian);
      expect(timer.state.remainingSeconds, 90 * 60);
      expect(timer.state.totalSeconds, 90 * 60);
      expect(timer.state.pomodorosPerCycle, 1);
      expect(timer.state.mode, PomodoroMode.work);
      expect(timer.state.isRunning, false);
    });

    test('switches back to pomodoro', () {
      timer
        ..switchStyle(TimerStyle.ultraradian)
        ..switchStyle(TimerStyle.pomodoro);
      expect(timer.timerStyle, TimerStyle.pomodoro);
      expect(timer.state.remainingSeconds, 25 * 60);
      expect(timer.state.totalSeconds, 25 * 60);
      expect(timer.state.pomodorosPerCycle, 4);
    });

    test('resets running timer when switching', () {
      timer.start();
      fakeController.tick();
      expect(timer.state.isRunning, true);

      timer.switchStyle(TimerStyle.ultraradian);
      expect(timer.state.isRunning, false);
      expect(timer.state.remainingSeconds, 90 * 60);
    });

    test('does nothing when switching to same style', () {
      timer.start();
      fakeController.tick();
      final stateBefore = timer.state;

      timer.switchStyle(TimerStyle.pomodoro);
      expect(timer.state, stateBefore);
    });

    test('notifies listeners', () {
      var notified = false;
      timer
        ..addListener(() => notified = true)
        ..switchStyle(TimerStyle.ultraradian);
      expect(notified, true);
    });

    test('resets completed pomodoros', () {
      timer.start();
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      expect(timer.state.completedPomodoros, 1);

      timer.switchStyle(TimerStyle.ultraradian);
      expect(timer.state.completedPomodoros, 0);
    });
  });

  group('timerStyle getter', () {
    test('defaults to pomodoro', () {
      expect(timer.timerStyle, TimerStyle.pomodoro);
    });
  });

  group('applyRemoteState()', () {
    test('applies remote state and notifies listeners', () {
      var notified = false;
      timer.addListener(() => notified = true);

      const remoteState = PomodoroState(
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
      const remoteState = PomodoroState(
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

  group('Session complete with services', () {
    late List<String> playedSounds;
    late List<_Call> notifyCalls;
    late SoundService soundService;
    late NotificationService notificationService;
    late PomodoroTimer timerWithServices;

    setUp(() {
      playedSounds = [];
      notifyCalls = [];

      soundService = SoundService(
        playCallback: (assetPath) async => playedSounds.add(assetPath),
      );

      notificationService = NotificationService(
        runProcess: (exec, args) async {
          notifyCalls.add(_Call(exec, args));
          return ProcessResult(0, 0, '(uint32 1,)', '');
        },
      );

      timerWithServices = PomodoroTimer(
        workMinutes: 1,
        shortBreakMinutes: 1,
        longBreakMinutes: 1,
        pomodorosPerCycle: 2,
        timerFactory: fakeTimerFactory,
        soundService: soundService,
        notificationService: notificationService,
      );
    });

    tearDown(() {
      timerWithServices.dispose();
    });

    test('calls sound and notification services on session complete', () {
      timerWithServices.start();
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }

      expect(playedSounds, isNotEmpty);
      // showSessionComplete was called (the Notify call after the initial
      // showTimer from start).
      final sessionCompleteCall = notifyCalls.where(
        (c) => c.args.any((a) => a.contains('complete!')),
      );
      expect(sessionCompleteCall, isNotEmpty);
    });

    test('long break completes and transitions to work', () {
      // Complete 2 work sessions to trigger long break.
      timerWithServices.start();
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      expect(timerWithServices.state.mode, PomodoroMode.shortBreak);

      timerWithServices.skip();
      expect(timerWithServices.state.mode, PomodoroMode.work);

      timerWithServices.start();
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      expect(timerWithServices.state.mode, PomodoroMode.longBreak);

      // Now complete the long break.
      timerWithServices.start();
      for (var i = 0; i < 60; i++) {
        fakeController.tick();
      }
      expect(timerWithServices.state.mode, PomodoroMode.work);
    });

    test('notification updates at 30-second intervals', () {
      timerWithServices.start();
      notifyCalls.clear();

      // Tick 30 times so remainingSeconds goes from 60 to 30.
      for (var i = 0; i < 30; i++) {
        fakeController.tick();
      }
      expect(timerWithServices.state.remainingSeconds, 30);

      // At 30 seconds remaining (divisible by 30), a notification update
      // should have been sent.
      final timerUpdates = notifyCalls.where(
        (c) => c.args.any(
          (a) => a.contains('org.freedesktop.Notifications.Notify'),
        ),
      );
      expect(timerUpdates, isNotEmpty);
    });
  });
}

/// Captured call for the mock process runner.
class _Call {
  _Call(this.executable, this.args);
  final String executable;
  final List<String> args;
}
