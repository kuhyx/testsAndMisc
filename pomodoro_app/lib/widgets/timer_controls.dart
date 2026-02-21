import 'package:flutter/material.dart';

import '../models/pomodoro_state.dart';
import '../theme/pomodoro_theme.dart';

/// Row of control buttons for the Pomodoro timer.
class TimerControls extends StatelessWidget {
  /// Creates [TimerControls].
  const TimerControls({
    required this.state,
    required this.onStart,
    required this.onPause,
    required this.onReset,
    required this.onSkip,
    super.key,
  });

  /// The current Pomodoro state.
  final PomodoroState state;

  /// Callback when user taps start.
  final VoidCallback onStart;

  /// Callback when user taps pause.
  final VoidCallback onPause;

  /// Callback when user taps reset.
  final VoidCallback onReset;

  /// Callback when user taps skip.
  final VoidCallback onSkip;

  @override
  Widget build(BuildContext context) {
    final color = PomodoroTheme.colorForMode(state.mode);

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Reset button.
        IconButton(
          onPressed: onReset,
          icon: const Icon(Icons.refresh),
          iconSize: 32,
          tooltip: 'Reset',
          color: Colors.white70,
        ),
        const SizedBox(width: 16),
        // Play / Pause button.
        SizedBox(
          width: 72,
          height: 72,
          child: ElevatedButton(
            onPressed: state.isRunning ? onPause : onStart,
            style: ElevatedButton.styleFrom(
              backgroundColor: color,
              foregroundColor: Colors.white,
              shape: const CircleBorder(),
              padding: EdgeInsets.zero,
            ),
            child: Icon(
              state.isRunning ? Icons.pause : Icons.play_arrow,
              size: 36,
            ),
          ),
        ),
        const SizedBox(width: 16),
        // Skip button.
        IconButton(
          onPressed: onSkip,
          icon: const Icon(Icons.skip_next),
          iconSize: 32,
          tooltip: 'Skip',
          color: Colors.white70,
        ),
      ],
    );
  }
}
