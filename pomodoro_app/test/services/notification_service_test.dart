import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pomodoro_app/models/pomodoro_state.dart';
import 'package:pomodoro_app/services/notification_service.dart';

/// Captured call to the mock process runner.
class _Call {
  _Call(this.executable, this.args);
  final String executable;
  final List<String> args;
}

void main() {
  group('NotificationService', () {
    late List<_Call> calls;
    late NotificationService service;

    Future<ProcessResult> mockRun(String exec, List<String> args) async {
      calls.add(_Call(exec, args));
      return ProcessResult(0, 0, '(uint32 42,)', '');
    }

    setUp(() {
      calls = [];
      service = NotificationService(runProcess: mockRun);
    });

    tearDown(() {
      service.dispose();
    });

    test('showTimer sends Notify via gdbus', () async {
      final state = PomodoroState(
        mode: PomodoroMode.work,
        remainingSeconds: 1500,
        totalSeconds: 1500,
        isRunning: true,
        completedPomodoros: 0,
        pomodorosPerCycle: 4,
      );

      await service.showTimer(state: state);

      expect(calls, hasLength(1));
      expect(calls[0].executable, 'gdbus');
      expect(
        calls[0].args,
        contains('org.freedesktop.Notifications.Notify'),
      );
      expect(calls[0].args, contains('Work \u2013 25:00'));
      expect(calls[0].args, contains("['pause', 'Pause', 'skip', 'Skip']"));
    });

    test('showTimer shows Start action when paused', () async {
      final state = PomodoroState(
        mode: PomodoroMode.shortBreak,
        remainingSeconds: 120,
        totalSeconds: 300,
        isRunning: false,
        completedPomodoros: 1,
        pomodorosPerCycle: 4,
      );

      await service.showTimer(state: state);

      expect(calls[0].args, contains("['start', 'Start']"));
    });

    test('showTimer replaces previous notification', () async {
      final state = PomodoroState(
        mode: PomodoroMode.work,
        remainingSeconds: 1500,
        totalSeconds: 1500,
        isRunning: true,
        completedPomodoros: 0,
        pomodorosPerCycle: 4,
      );

      await service.showTimer(state: state);

      // First call should use replaces_id 0.
      expect(calls[0].args, contains('0'));

      // Second call should use the parsed ID 42.
      await service.showTimer(state: state);
      expect(calls[1].args, contains('42'));
    });

    test('parses notification ID from gdbus output', () async {
      final state = PomodoroState.initial();

      await service.showTimer(state: state);
      expect(service.currentId, 42);
    });

    test('handles unparsable gdbus output gracefully', () async {
      final stubService = NotificationService(
        runProcess: (exec, args) async {
          return ProcessResult(0, 0, 'unexpected output', '');
        },
      );

      final state = PomodoroState.initial();
      await stubService.showTimer(state: state);
      expect(stubService.currentId, 0);

      stubService.dispose();
    });

    test('showSessionComplete sends correct content', () async {
      await service.showSessionComplete(
        completedMode: PomodoroMode.work,
        nextMode: PomodoroMode.shortBreak,
      );

      expect(calls, hasLength(1));
      expect(calls[0].args, contains('Work complete!'));
      expect(calls[0].args, contains('Up next: Short Break'));
    });

    test('cancel sends CloseNotification', () async {
      // First show a notification to get an ID.
      final state = PomodoroState.initial();
      await service.showTimer(state: state);
      calls.clear();

      await service.cancel();

      expect(calls, hasLength(1));
      expect(
        calls[0].args,
        contains('org.freedesktop.Notifications.CloseNotification'),
      );
      expect(calls[0].args, contains('42'));
    });

    test('cancel does nothing when no notification shown', () async {
      await service.cancel();
      expect(calls, isEmpty);
    });

    test('cancel resets currentId to 0', () async {
      final state = PomodoroState.initial();
      await service.showTimer(state: state);
      expect(service.currentId, 42);

      await service.cancel();
      expect(service.currentId, 0);
    });

    test('does nothing after dispose', () async {
      service.dispose();

      final state = PomodoroState.initial();
      await service.showTimer(state: state);
      await service.showSessionComplete(
        completedMode: PomodoroMode.work,
        nextMode: PomodoroMode.shortBreak,
      );
      await service.cancel();

      expect(calls, isEmpty);
    });

    test('dispose cancels active notification', () async {
      final state = PomodoroState.initial();
      await service.showTimer(state: state);
      calls.clear();

      service.dispose();

      // Cancel was fired (fire-and-forget).
      expect(calls, hasLength(1));
      expect(
        calls[0].args,
        contains('org.freedesktop.Notifications.CloseNotification'),
      );
    });

    test('handles process error gracefully', () async {
      final errorService = NotificationService(
        runProcess: (exec, args) async {
          throw const OSError('gdbus not found');
        },
      );

      final state = PomodoroState.initial();
      // Should not throw.
      await errorService.showTimer(state: state);
      await errorService.cancel();

      errorService.dispose();
    });
  });

  group('progressBar', () {
    test('returns empty bar at 0%', () {
      expect(NotificationService.progressBar(0.0), '░' * 20);
    });

    test('returns full bar at 100%', () {
      expect(NotificationService.progressBar(1.0), '█' * 20);
    });

    test('returns half bar at 50%', () {
      final bar = NotificationService.progressBar(0.5);
      expect(bar, '${'█' * 10}${'░' * 10}');
    });
  });
}
