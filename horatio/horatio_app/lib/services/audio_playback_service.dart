import 'package:audioplayers/audioplayers.dart';

/// Playback status for the audio player.
enum PlaybackStatus {
  /// Not playing.
  idle,

  /// Currently playing audio.
  playing,

  /// Playback finished.
  completed,
}

/// Wraps [AudioPlayer] for audio playback.
class AudioPlaybackService {
  /// Creates an [AudioPlaybackService].
  AudioPlaybackService({AudioPlayer? player})
      : _player = player;

  AudioPlayer? _player;

  AudioPlayer get _activePlayer => _player ??= AudioPlayer();

  /// Plays audio from a local file path.
  Future<void> play(String filePath) =>
      _activePlayer.play(DeviceFileSource(filePath));

  /// Stops playback.
  Future<void> stop() => _activePlayer.stop();

  /// Stream of playback status changes.
  Stream<PlaybackStatus> get status =>
      _activePlayer.onPlayerStateChanged.map((state) => switch (state) {
            PlayerState.playing => PlaybackStatus.playing,
            PlayerState.completed => PlaybackStatus.completed,
            _ => PlaybackStatus.idle,
          });

  /// Stream of playback position.
  Stream<Duration> get position => _activePlayer.onPositionChanged;

  /// Releases the player resources.
  Future<void> dispose() async {
    final player = _player;
    if (player != null) {
      await player.dispose();
    }
  }
}
