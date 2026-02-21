import 'dart:math';

import 'package:flutter/material.dart';

import '../models/pomodoro_state.dart';
import '../theme/pomodoro_theme.dart';

/// A circular progress indicator that displays the remaining time.
class TimerDisplay extends StatelessWidget {
  /// Creates a [TimerDisplay].
  const TimerDisplay({
    required this.state,
    super.key,
  });

  /// The current Pomodoro state.
  final PomodoroState state;

  @override
  Widget build(BuildContext context) {
    final color = PomodoroTheme.colorForMode(state.mode);

    return LayoutBuilder(
      builder: (context, constraints) {
        final size = min(constraints.maxWidth, constraints.maxHeight) * 0.7;
        return SizedBox(
          width: size,
          height: size,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Background circle.
              SizedBox.expand(
                child: CircularProgressIndicator(
                  value: 1.0,
                  strokeWidth: 8,
                  color: color.withValues(alpha: 0.2),
                ),
              ),
              // Progress arc.
              SizedBox.expand(
                child: CircularProgressIndicator(
                  value: state.progress,
                  strokeWidth: 8,
                  color: color,
                  strokeCap: StrokeCap.round,
                ),
              ),
              // Time text and mode label.
              FittedBox(
                fit: BoxFit.scaleDown,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      state.modeDisplayLabel,
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                            color: color,
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      state.formattedTime,
                      style:
                          Theme.of(context).textTheme.displayLarge?.copyWith(
                                color: Colors.white,
                              ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
