import 'package:flutter_test/flutter_test.dart';
import 'package:pomodoro_app/models/pomodoro_state.dart';
import 'package:pomodoro_app/theme/pomodoro_theme.dart';

void main() {
  group('PomodoroTheme.colorForMode', () {
    test('returns longBreakColor for longBreak', () {
      expect(
        PomodoroTheme.colorForMode(PomodoroMode.longBreak),
        PomodoroTheme.longBreakColor,
      );
    });
  });
}
