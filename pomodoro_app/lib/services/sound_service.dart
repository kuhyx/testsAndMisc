import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';

import '../models/pomodoro_state.dart';

/// Plays notification sounds for Pomodoro timer transitions.
///
/// Each transition type has a distinct sound:
/// - Work done → ascending chime
/// - Short break done → gentle double ping
/// - Long break starting → descending celebration
/// - Long break done → rapid wake-up beeps
class SoundService {
  /// Creates a [SoundService].
  ///
  /// Pass a custom [playCallback] for testing.
  SoundService({
    @visibleForTesting Future<void> Function(String assetPath)? playCallback,
  }) : _playCallback = playCallback;

  final Future<void> Function(String assetPath)? _playCallback;
  AudioPlayer? _player;
  bool _disposed = false;

  static const _assetPrefix = 'sounds';

  /// Plays the appropriate sound for a mode transition.
  ///
  /// [completedMode] is the mode that just finished.
  /// [nextMode] is the mode that is starting.
  Future<void> playTransitionSound({
    required PomodoroMode completedMode,
    required PomodoroMode nextMode,
  }) async {
    if (_disposed) return;

    final assetPath = _assetForTransition(completedMode, nextMode);
    if (assetPath == null) return;

    try {
      if (_playCallback != null) {
        await _playCallback(assetPath);
      } else {
        _player?.dispose();
        _player = AudioPlayer();
        await _player!.play(AssetSource('$_assetPrefix/$assetPath'));
      }
      debugPrint('SoundService: Playing $assetPath');
    } on Object catch (e) {
      debugPrint('SoundService: Playback error: $e');
    }
  }

  /// Returns the WAV filename for a given transition, or null if none.
  static String? _assetForTransition(
    PomodoroMode completedMode,
    PomodoroMode nextMode,
  ) {
    switch (completedMode) {
      case PomodoroMode.work:
        if (nextMode == PomodoroMode.longBreak) {
          return 'long_break_start.wav';
        }
        return 'work_done.wav';
      case PomodoroMode.shortBreak:
        return 'short_break_done.wav';
      case PomodoroMode.longBreak:
        return 'long_break_done.wav';
    }
  }

  /// Releases audio resources.
  void dispose() {
    _disposed = true;
    _player?.dispose();
    _player = null;
  }
}
