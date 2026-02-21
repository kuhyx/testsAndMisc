import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/pomodoro_state.dart';
import 'notification_service.dart';
import 'sound_service.dart';
import 'sync_service.dart';

/// Manages the Pomodoro timer logic, independent of UI framework.
///
/// Optionally synchronizes state across devices via [SyncService].
class PomodoroTimer extends ChangeNotifier {
  /// Creates a [PomodoroTimer] with configurable durations.
  PomodoroTimer({
    int? workMinutes,
    int? shortBreakMinutes,
    int? longBreakMinutes,
    int? pomodorosPerCycle,
    TimerStyle timerStyle = TimerStyle.pomodoro,
    this.syncService,
    SoundService? soundService,
    NotificationService? notificationService,
    @visibleForTesting Timer Function(Duration, void Function(Timer))? timerFactory,
  })  : _timerStyle = timerStyle,
        _soundService = soundService,
        _notificationService = notificationService,
        _timerFactory = timerFactory ?? Timer.periodic {
    _workMinutes = workMinutes ?? timerStyle.defaultWorkMinutes;
    _shortBreakMinutes = shortBreakMinutes ?? timerStyle.defaultShortBreakMinutes;
    _longBreakMinutes = longBreakMinutes ?? timerStyle.defaultLongBreakMinutes;
    _pomodorosPerCycle = pomodorosPerCycle ?? timerStyle.defaultPomodorosPerCycle;
    _state = PomodoroState.initial(
      workMinutes: _workMinutes,
      shortBreakMinutes: _shortBreakMinutes,
      longBreakMinutes: _longBreakMinutes,
      pomodorosPerCycle: _pomodorosPerCycle,
    );
  }

  /// Duration of a work session in minutes.
  late int _workMinutes;

  /// Duration of a short break in minutes.
  late int _shortBreakMinutes;

  /// Duration of a long break in minutes.
  late int _longBreakMinutes;

  /// Number of work sessions before a long break.
  late int _pomodorosPerCycle;

  /// The current timer style.
  TimerStyle _timerStyle;

  /// Optional sync service for LAN synchronization.
  final SyncService? syncService;

  final SoundService? _soundService;
  final NotificationService? _notificationService;
  final Timer Function(Duration, void Function(Timer)) _timerFactory;

  late PomodoroState _state;
  Timer? _timer;

  /// Whether we are currently applying a remote state (prevents echo).
  bool _applyingRemote = false;

  /// The current state of the timer.
  PomodoroState get state => _state;

  /// The active timer style.
  TimerStyle get timerStyle => _timerStyle;

  /// Switches to a different timer style, resetting all progress.
  void switchStyle(TimerStyle style) {
    if (style == _timerStyle) return;
    _timer?.cancel();
    _timer = null;
    _timerStyle = style;
    _workMinutes = style.defaultWorkMinutes;
    _shortBreakMinutes = style.defaultShortBreakMinutes;
    _longBreakMinutes = style.defaultLongBreakMinutes;
    _pomodorosPerCycle = style.defaultPomodorosPerCycle;
    _state = PomodoroState.initial(
      workMinutes: _workMinutes,
      shortBreakMinutes: _shortBreakMinutes,
      longBreakMinutes: _longBreakMinutes,
      pomodorosPerCycle: _pomodorosPerCycle,
    );
    _notificationService?.cancel();
    notifyListeners();
    syncService?.stopHeartbeat();
  }

  /// Starts or resumes the timer.
  void start() {
    if (_state.isRunning) return;
    _state = _state.copyWith(isRunning: true);
    notifyListeners();
    _startTicking();
    _notificationService?.showTimer(state: _state);
    _broadcastIfLocal('start');
    syncService?.startHeartbeat(() => _state);
  }

  /// Pauses the timer.
  void pause() {
    if (!_state.isRunning) return;
    _timer?.cancel();
    _timer = null;
    _state = _state.copyWith(isRunning: false);
    _notificationService?.cancel();
    notifyListeners();
    _broadcastIfLocal('pause');
    syncService?.stopHeartbeat();
  }

  /// Resets the current session timer without changing the mode.
  void reset() {
    _timer?.cancel();
    _timer = null;
    _state = _state.copyWith(
      remainingSeconds: _state.totalSeconds,
      isRunning: false,
    );
    _notificationService?.cancel();
    notifyListeners();
    _broadcastIfLocal('reset');
    syncService?.stopHeartbeat();
  }

  /// Skips to the next session, treating the current one as completed.
  void skip() {
    _timer?.cancel();
    _timer = null;
    _onSessionComplete();
    _broadcastIfLocal('skip');
    syncService?.stopHeartbeat();
  }

  /// Applies state received from a remote device via [SyncService].
  void applyRemoteState(PomodoroState remoteState, String action) {
    _applyingRemote = true;

    _timer?.cancel();
    _timer = null;

    _state = remoteState;

    if (_state.isRunning) {
      _startTicking();
    }

    notifyListeners();
    _applyingRemote = false;
  }

  void _tick(Timer timer) {
    if (_state.remainingSeconds <= 1) {
      timer.cancel();
      _timer = null;
      _onSessionComplete();
    } else {
      _state = _state.copyWith(
        remainingSeconds: _state.remainingSeconds - 1,
      );
      _updateNotification();
      notifyListeners();
    }
  }

  void _onSessionComplete() {
    if (_state.mode == PomodoroMode.work) {
      final newCompleted = _state.completedPomodoros + 1;
      _state = _state.copyWith(
        completedPomodoros: newCompleted,
        remainingSeconds: 0,
        isRunning: false,
      );
    } else {
      _state = _state.copyWith(
        remainingSeconds: 0,
        isRunning: false,
      );
    }
    notifyListeners();
    final completedMode = _state.mode;
    _advanceToNextMode();
    _soundService?.playTransitionSound(
      completedMode: completedMode,
      nextMode: _state.mode,
    );
    _notificationService?.showSessionComplete(
      completedMode: completedMode,
      nextMode: _state.mode,
    );
    notifyListeners();
  }

  void _advanceToNextMode() {
    switch (_state.mode) {
      case PomodoroMode.work:
        if (_state.completedPomodoros > 0 &&
            _state.completedPomodoros % _pomodorosPerCycle == 0) {
          _setMode(PomodoroMode.longBreak);
        } else {
          _setMode(PomodoroMode.shortBreak);
        }
      case PomodoroMode.shortBreak:
      case PomodoroMode.longBreak:
        _setMode(PomodoroMode.work);
    }
  }

  void _setMode(PomodoroMode mode) {
    final totalSeconds = _durationForMode(mode) * 60;
    _state = _state.copyWith(
      mode: mode,
      remainingSeconds: totalSeconds,
      totalSeconds: totalSeconds,
      isRunning: false,
    );
  }

  int _durationForMode(PomodoroMode mode) {
    switch (mode) {
      case PomodoroMode.work:
        return _workMinutes;
      case PomodoroMode.shortBreak:
        return _shortBreakMinutes;
      case PomodoroMode.longBreak:
        return _longBreakMinutes;
    }
  }

  void _startTicking() {
    _timer = _timerFactory(
      const Duration(seconds: 1),
      _tick,
    );
  }

  /// Broadcasts state to peers only if this is a local user action.
  void _broadcastIfLocal(String action) {
    if (!_applyingRemote) {
      syncService?.broadcast(_state, action);
    }
  }

  /// Interval in seconds between notification updates while running.
  static const _notifyIntervalSeconds = 30;

  void _updateNotification() {
    if (_notificationService == null) return;
    if (_state.remainingSeconds % _notifyIntervalSeconds == 0) {
      _notificationService.showTimer(state: _state);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    syncService?.stopHeartbeat();
    _soundService?.dispose();
    _notificationService?.dispose();
    super.dispose();
  }
}
