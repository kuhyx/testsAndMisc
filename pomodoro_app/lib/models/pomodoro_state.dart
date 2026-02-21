/// Defines the timer style (technique) the user can choose.
enum TimerStyle {
  /// Classic Pomodoro: 25 min work, 5 min short break, 15 min long break.
  pomodoro,

  /// Ultraradian rhythm: 90 min work, 30 min break.
  ultraradian,
}

/// Extension on [TimerStyle] to provide display labels and default durations.
extension TimerStyleConfig on TimerStyle {
  /// Human-readable label for the timer style.
  String get label {
    switch (this) {
      case TimerStyle.pomodoro:
        return 'Pomodoro';
      case TimerStyle.ultraradian:
        return 'Ultraradian';
    }
  }

  /// Default work duration in minutes.
  int get defaultWorkMinutes {
    switch (this) {
      case TimerStyle.pomodoro:
        return 25;
      case TimerStyle.ultraradian:
        return 90;
    }
  }

  /// Default short break duration in minutes.
  int get defaultShortBreakMinutes {
    switch (this) {
      case TimerStyle.pomodoro:
        return 5;
      case TimerStyle.ultraradian:
        return 30;
    }
  }

  /// Default long break duration in minutes.
  int get defaultLongBreakMinutes {
    switch (this) {
      case TimerStyle.pomodoro:
        return 15;
      case TimerStyle.ultraradian:
        return 30;
    }
  }

  /// Default number of work sessions before a long break.
  int get defaultPomodorosPerCycle {
    switch (this) {
      case TimerStyle.pomodoro:
        return 4;
      case TimerStyle.ultraradian:
        return 1;
    }
  }
}

/// Defines the different modes of a Pomodoro session.
enum PomodoroMode {
  /// A work session (default 25 minutes).
  work,

  /// A short break between work sessions (default 5 minutes).
  shortBreak,

  /// A long break after completing a cycle (default 15 minutes).
  longBreak,
}

/// Extension on [PomodoroMode] to provide display labels.
extension PomodoroModeLabel on PomodoroMode {
  /// Human-readable label for the mode.
  String get label {
    switch (this) {
      case PomodoroMode.work:
        return 'Work';
      case PomodoroMode.shortBreak:
        return 'Short Break';
      case PomodoroMode.longBreak:
        return 'Long Break';
    }
  }
}

/// Immutable snapshot of the Pomodoro timer state.
class PomodoroState {
  /// Creates a [PomodoroState].
  const PomodoroState({
    required this.mode,
    required this.remainingSeconds,
    required this.totalSeconds,
    required this.isRunning,
    required this.completedPomodoros,
    required this.pomodorosPerCycle,
  });

  /// Creates the default initial state.
  factory PomodoroState.initial({
    int workMinutes = 25,
    int shortBreakMinutes = 5,
    int longBreakMinutes = 15,
    int pomodorosPerCycle = 4,
  }) {
    final totalSeconds = workMinutes * 60;
    return PomodoroState(
      mode: PomodoroMode.work,
      remainingSeconds: totalSeconds,
      totalSeconds: totalSeconds,
      isRunning: false,
      completedPomodoros: 0,
      pomodorosPerCycle: pomodorosPerCycle,
    );
  }

  /// The current timer mode.
  final PomodoroMode mode;

  /// Seconds left on the current timer.
  final int remainingSeconds;

  /// Total seconds for the current mode.
  final int totalSeconds;

  /// Whether the timer is currently running.
  final bool isRunning;

  /// Number of completed work sessions in the current cycle.
  final int completedPomodoros;

  /// Number of pomodoros before a long break.
  final int pomodorosPerCycle;

  /// Progress as a value between 0.0 and 1.0.
  double get progress {
    if (totalSeconds == 0) return 1.0;
    return 1.0 - (remainingSeconds / totalSeconds);
  }

  /// Display label for the current mode, context-aware.
  ///
  /// When [pomodorosPerCycle] is 1 (e.g. ultraradian), breaks are simply
  /// labelled "Break" instead of "Short Break" or "Long Break".
  String get modeDisplayLabel {
    if (pomodorosPerCycle <= 1 && mode != PomodoroMode.work) {
      return 'Break';
    }
    return mode.label;
  }

  /// Formatted time string (MM:SS).
  String get formattedTime {
    final minutes = remainingSeconds ~/ 60;
    final seconds = remainingSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:'
        '${seconds.toString().padLeft(2, '0')}';
  }

  /// Creates a copy with the given fields replaced.
  PomodoroState copyWith({
    PomodoroMode? mode,
    int? remainingSeconds,
    int? totalSeconds,
    bool? isRunning,
    int? completedPomodoros,
    int? pomodorosPerCycle,
  }) {
    return PomodoroState(
      mode: mode ?? this.mode,
      remainingSeconds: remainingSeconds ?? this.remainingSeconds,
      totalSeconds: totalSeconds ?? this.totalSeconds,
      isRunning: isRunning ?? this.isRunning,
      completedPomodoros: completedPomodoros ?? this.completedPomodoros,
      pomodorosPerCycle: pomodorosPerCycle ?? this.pomodorosPerCycle,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is PomodoroState &&
        other.mode == mode &&
        other.remainingSeconds == remainingSeconds &&
        other.totalSeconds == totalSeconds &&
        other.isRunning == isRunning &&
        other.completedPomodoros == completedPomodoros &&
        other.pomodorosPerCycle == pomodorosPerCycle;
  }

  @override
  int get hashCode {
    return Object.hash(
      mode,
      remainingSeconds,
      totalSeconds,
      isRunning,
      completedPomodoros,
      pomodorosPerCycle,
    );
  }
}
