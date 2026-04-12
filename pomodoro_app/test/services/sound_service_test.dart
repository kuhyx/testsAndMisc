import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pomodoro_app/models/pomodoro_state.dart';
import 'package:pomodoro_app/services/sound_service.dart';

/// A minimal fake [AudioPlayer] for testing the production path.
///
/// Uses [implements] + [noSuchMethod] to avoid calling the real
/// AudioPlayer constructor which requires platform bindings.
class _FakeAudioPlayer implements AudioPlayer {
  bool playCalled = false;

  @override
  Future<void> play(
    Source source, {
    double? volume,
    double? balance,
    AudioContext? ctx,
    Duration? position,
    PlayerMode? mode,
  }) async {
    playCalled = true;
  }

  @override
  Future<void> dispose() async {}

  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

void main() {
  group('SoundService', () {
    late List<String> playedAssets;
    late SoundService service;

    setUp(() {
      playedAssets = [];
      service = SoundService(
        playCallback: (assetPath) async => playedAssets.add(assetPath),
      );
    });

    tearDown(() {
      service.dispose();
    });

    test('plays work_done when work ends with short break next', () async {
      await service.playTransitionSound(
        completedMode: PomodoroMode.work,
        nextMode: PomodoroMode.shortBreak,
      );
      expect(playedAssets, ['work_done.wav']);
    });

    test('plays long_break_start when work ends with long break next',
        () async {
      await service.playTransitionSound(
        completedMode: PomodoroMode.work,
        nextMode: PomodoroMode.longBreak,
      );
      expect(playedAssets, ['long_break_start.wav']);
    });

    test('plays short_break_done when short break ends', () async {
      await service.playTransitionSound(
        completedMode: PomodoroMode.shortBreak,
        nextMode: PomodoroMode.work,
      );
      expect(playedAssets, ['short_break_done.wav']);
    });

    test('plays long_break_done when long break ends', () async {
      await service.playTransitionSound(
        completedMode: PomodoroMode.longBreak,
        nextMode: PomodoroMode.work,
      );
      expect(playedAssets, ['long_break_done.wav']);
    });

    test('does nothing after dispose', () async {
      service.dispose();
      await service.playTransitionSound(
        completedMode: PomodoroMode.work,
        nextMode: PomodoroMode.shortBreak,
      );
      expect(playedAssets, isEmpty);
    });

    test('handles playback error gracefully', () async {
      final errorService = SoundService(
        playCallback: (assetPath) async {
          throw Exception('audio error');
        },
      );

      // Should not throw.
      await errorService.playTransitionSound(
        completedMode: PomodoroMode.work,
        nextMode: PomodoroMode.shortBreak,
      );

      errorService.dispose();
    });

    test('uses player factory for production path', () async {
      final fakePlayer = _FakeAudioPlayer();

      final factoryService = SoundService(
        playerFactory: () => fakePlayer,
      );

      await factoryService.playTransitionSound(
        completedMode: PomodoroMode.work,
        nextMode: PomodoroMode.shortBreak,
      );

      expect(fakePlayer.playCalled, true);
      factoryService.dispose();
    });

    test('disposes previous player on subsequent plays', () async {
      final factoryService = SoundService(
        playerFactory: _FakeAudioPlayer.new,
      );

      await factoryService.playTransitionSound(
        completedMode: PomodoroMode.work,
        nextMode: PomodoroMode.shortBreak,
      );

      // Play again — should dispose the previous player.
      await factoryService.playTransitionSound(
        completedMode: PomodoroMode.shortBreak,
        nextMode: PomodoroMode.work,
      );

      factoryService.dispose();
    });
  });
}
