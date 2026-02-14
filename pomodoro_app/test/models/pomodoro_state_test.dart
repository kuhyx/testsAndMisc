import 'package:flutter_test/flutter_test.dart';
import 'package:pomodoro_app/models/pomodoro_state.dart';

void main() {
  group('PomodoroMode', () {
    test('label returns correct strings', () {
      expect(PomodoroMode.work.label, 'Work');
      expect(PomodoroMode.shortBreak.label, 'Short Break');
      expect(PomodoroMode.longBreak.label, 'Long Break');
    });
  });

  group('PomodoroState.initial', () {
    test('creates default state', () {
      final state = PomodoroState.initial();
      expect(state.mode, PomodoroMode.work);
      expect(state.remainingSeconds, 25 * 60);
      expect(state.totalSeconds, 25 * 60);
      expect(state.isRunning, false);
      expect(state.completedPomodoros, 0);
      expect(state.pomodorosPerCycle, 4);
    });

    test('creates state with custom durations', () {
      final state = PomodoroState.initial(
        workMinutes: 30,
        shortBreakMinutes: 10,
        longBreakMinutes: 20,
        pomodorosPerCycle: 3,
      );
      expect(state.remainingSeconds, 30 * 60);
      expect(state.totalSeconds, 30 * 60);
      expect(state.pomodorosPerCycle, 3);
    });
  });

  group('PomodoroState.progress', () {
    test('returns 0.0 at start', () {
      final state = PomodoroState.initial();
      expect(state.progress, 0.0);
    });

    test('returns 0.5 at halfway', () {
      final state = PomodoroState.initial().copyWith(
        remainingSeconds: 25 * 30, // half of 25*60
      );
      expect(state.progress, closeTo(0.5, 0.001));
    });

    test('returns 1.0 when totalSeconds is 0', () {
      final state = PomodoroState.initial().copyWith(
        totalSeconds: 0,
        remainingSeconds: 0,
      );
      expect(state.progress, 1.0);
    });

    test('returns close to 1.0 at end', () {
      final state = PomodoroState.initial().copyWith(remainingSeconds: 0);
      expect(state.progress, 1.0);
    });
  });

  group('PomodoroState.formattedTime', () {
    test('formats full time correctly', () {
      final state = PomodoroState.initial(); // 25:00
      expect(state.formattedTime, '25:00');
    });

    test('formats single-digit minutes with padding', () {
      final state = PomodoroState.initial().copyWith(remainingSeconds: 5 * 60 + 30);
      expect(state.formattedTime, '05:30');
    });

    test('formats zero correctly', () {
      final state = PomodoroState.initial().copyWith(remainingSeconds: 0);
      expect(state.formattedTime, '00:00');
    });

    test('formats seconds with padding', () {
      final state = PomodoroState.initial().copyWith(remainingSeconds: 60 + 5);
      expect(state.formattedTime, '01:05');
    });
  });

  group('PomodoroState.copyWith', () {
    test('copies with mode change', () {
      final original = PomodoroState.initial();
      final copy = original.copyWith(mode: PomodoroMode.shortBreak);
      expect(copy.mode, PomodoroMode.shortBreak);
      expect(copy.remainingSeconds, original.remainingSeconds);
    });

    test('preserves values when no parameters given', () {
      final original = PomodoroState.initial();
      final copy = original.copyWith();
      expect(copy, original);
    });
  });

  group('PomodoroState equality', () {
    test('equal states are ==', () {
      final a = PomodoroState.initial();
      final b = PomodoroState.initial();
      expect(a, b);
      expect(a.hashCode, b.hashCode);
    });

    test('different states are !=', () {
      final a = PomodoroState.initial();
      final b = a.copyWith(remainingSeconds: 100);
      expect(a, isNot(b));
    });

    test('identical references are ==', () {
      final a = PomodoroState.initial();
      // ignore: prefer_const_declarations
      final b = a;
      expect(identical(a, b), true);
      expect(a, b);
    });

    test('different type is !=', () {
      final a = PomodoroState.initial();
      // ignore: unrelated_type_equality_checks
      expect(a == 'not a state', false);
    });
  });
}
