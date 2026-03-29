import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:mocktail/mocktail.dart';

class MockAudioPlayer extends Mock implements AudioPlayer {}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late MockAudioPlayer mockPlayer;
  late AudioPlaybackService service;

  setUpAll(() {
    registerFallbackValue(DeviceFileSource(''));
  });

  setUp(() {
    mockPlayer = MockAudioPlayer();
    service = AudioPlaybackService(player: mockPlayer);
    when(() => mockPlayer.onPlayerStateChanged)
        .thenAnswer((_) => const Stream.empty());
    when(() => mockPlayer.onPositionChanged)
        .thenAnswer((_) => const Stream.empty());
    when(() => mockPlayer.dispose()).thenAnswer((_) async {});
  });

  tearDown(() async {
    await service.dispose();
  });

  group('AudioPlaybackService', () {
    test('constructor works with default AudioPlayer', () async {
      final defaultService = AudioPlaybackService();
      await defaultService.dispose();
    });

    test('play calls player.play with DeviceFileSource', () async {
      when(() => mockPlayer.play(any())).thenAnswer((_) async {});

      await service.play('/tmp/test.m4a');

      verify(() => mockPlayer.play(any(that: isA<DeviceFileSource>())))
          .called(1);
    });

    test('stop calls player.stop', () async {
      when(() => mockPlayer.stop()).thenAnswer((_) async {});

      await service.stop();

      verify(() => mockPlayer.stop()).called(1);
    });

    test('status stream maps player state changes', () async {
      final controller = StreamController<PlayerState>();
      when(() => mockPlayer.onPlayerStateChanged)
          .thenAnswer((_) => controller.stream);
      final service2 = AudioPlaybackService(player: mockPlayer);

      final statuses = <PlaybackStatus>[];
      final sub = service2.status.listen(statuses.add);

      controller
        ..add(PlayerState.playing)
        ..add(PlayerState.completed)
        ..add(PlayerState.stopped)
        ..add(PlayerState.paused);

      await Future<void>.delayed(Duration.zero);
      expect(statuses, [
        PlaybackStatus.playing,
        PlaybackStatus.completed,
        PlaybackStatus.idle,
        PlaybackStatus.idle,
      ]);

      await sub.cancel();
      await controller.close();
      await service2.dispose();
    });

    test('position stream delegates', () async {
      final controller = StreamController<Duration>();
      when(() => mockPlayer.onPositionChanged)
          .thenAnswer((_) => controller.stream);
      final service2 = AudioPlaybackService(player: mockPlayer);

      final positions = <Duration>[];
      final sub = service2.position.listen(positions.add);

      controller
        ..add(const Duration(seconds: 1))
        ..add(const Duration(seconds: 2));

      await Future<void>.delayed(Duration.zero);
      expect(positions, [
        const Duration(seconds: 1),
        const Duration(seconds: 2),
      ]);

      await sub.cancel();
      await controller.close();
      await service2.dispose();
    });

    test('dispose calls player.dispose', () async {
      await service.dispose();

      verify(() => mockPlayer.dispose()).called(1);
    });
  });
}
