import 'dart:io';

import 'package:flutter/foundation.dart';

import '../models/pomodoro_state.dart';

/// Sends desktop notifications showing Pomodoro timer status.
///
/// Uses the freedesktop D-Bus Notifications interface via `gdbus` to show,
/// update, and dismiss notifications. The notification includes the current
/// mode, remaining time, and a progress bar. Action buttons (Pause / Skip /
/// Start) are displayed for quick interaction.
class NotificationService {
  /// Creates a [NotificationService].
  ///
  /// Pass a custom [runProcess] for testing.
  NotificationService({
    @visibleForTesting
    Future<ProcessResult> Function(String, List<String>)? runProcess,
  }) : _runProcess = runProcess ?? Process.run;

  final Future<ProcessResult> Function(String, List<String>) _runProcess;
  int _currentId = 0;
  bool _disposed = false;

  static const _dbusDest = 'org.freedesktop.Notifications';
  static const _dbusPath = '/org/freedesktop/Notifications';

  /// The notification ID currently shown (0 means none).
  @visibleForTesting
  int get currentId => _currentId;

  /// Shows or updates the timer notification with the current [state].
  ///
  /// The notification replaces any previous one so only a single
  /// notification is visible at a time.
  Future<void> showTimer({required PomodoroState state}) async {
    if (_disposed) return;

    final title = '${state.mode.label} \u2013 ${state.formattedTime}';
    final body = _progressBar(state.progress);

    await _notify(
      title: title,
      body: body,
      actions: state.isRunning
          ? ['pause', 'Pause', 'skip', 'Skip']
          : ['start', 'Start'],
    );
  }

  /// Shows a notification that the session has completed.
  Future<void> showSessionComplete({
    required PomodoroMode completedMode,
    required PomodoroMode nextMode,
  }) async {
    if (_disposed) return;

    final title = '${completedMode.label} complete!';
    final body = 'Up next: ${nextMode.label}';

    await _notify(title: title, body: body, actions: ['start', 'Start']);
  }

  /// Cancels the currently shown notification.
  Future<void> cancel() async {
    if (_disposed || _currentId == 0) return;

    try {
      await _runProcess('gdbus', [
        'call',
        '--session',
        '--dest',
        _dbusDest,
        '--object-path',
        _dbusPath,
        '--method',
        'org.freedesktop.Notifications.CloseNotification',
        '$_currentId',
      ]);
    } on Object catch (e) {
      debugPrint('NotificationService: Close error: $e');
    }
    _currentId = 0;
  }

  /// Releases resources. Does not await the underlying cancel.
  void dispose() {
    if (_disposed) return;
    if (_currentId != 0) {
      // Fire-and-forget; the notification daemon cleans up on exit.
      unawaited(cancel());
    }
    _disposed = true;
  }

  // ------------------------------------------------------------------
  // Private helpers
  // ------------------------------------------------------------------

  Future<void> _notify({
    required String title,
    required String body,
    List<String> actions = const [],
  }) async {
    final actionsStr = actions.isEmpty
        ? '[]'
        : '[${actions.map((a) => "'$a'").join(', ')}]';

    try {
      final result = await _runProcess('gdbus', [
        'call',
        '--session',
        '--dest',
        _dbusDest,
        '--object-path',
        _dbusPath,
        '--method',
        'org.freedesktop.Notifications.Notify',
        'Pomodoro',
        '$_currentId',
        'appointment-soon',
        title,
        body,
        actionsStr,
        '{}',
        '0',
      ]);

      final match =
          RegExp(r'\(uint32 (\d+),?\)').firstMatch(result.stdout as String);
      if (match != null) {
        _currentId = int.parse(match.group(1)!);
      }
    } on Object catch (e) {
      debugPrint('NotificationService: Notify error: $e');
    }
  }

  /// Builds a text-based progress bar for the notification body.
  @visibleForTesting
  static String progressBar(double progress) => _progressBar(progress);

  static String _progressBar(double progress) {
    const total = 20;
    final filled = (progress * total).round();
    final empty = total - filled;
    return '${'█' * filled}${'░' * empty}';
  }
}

/// Completes a future without requiring `await`.
///
/// Prevents the `unawaited_futures` lint in fire-and-forget calls.
void unawaited(Future<void> future) {}
