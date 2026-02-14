import 'package:flutter_test/flutter_test.dart';
import 'package:pomodoro_app/models/pomodoro_state.dart';
import 'package:pomodoro_app/services/sound_service.dart';

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
  });
}
