import 'package:flutter/material.dart';

import 'package:pomodoro_app/models/pomodoro_state.dart';
import 'package:pomodoro_app/theme/pomodoro_theme.dart';

/// Shows completed pomodoro indicators as filled/unfilled dots.
class PomodoroIndicators extends StatelessWidget {
  /// Creates [PomodoroIndicators].
  const PomodoroIndicators({
    required this.state,
    super.key,
  });

  /// The current Pomodoro state.
  final PomodoroState state;

  @override
  Widget build(BuildContext context) => Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(
        state.pomodorosPerCycle,
        (index) {
          final isCompleted = index < state.completedPomodoros % state.pomodorosPerCycle;
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              width: 14,
              height: 14,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isCompleted
                    ? PomodoroTheme.workColor
                    : Colors.white24,
                border: Border.all(
                  color: PomodoroTheme.workColor.withValues(alpha: 0.5),
                  width: 2,
                ),
              ),
            ),
          );
        },
      ),
    );
}
