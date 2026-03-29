import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/recording/recording_cubit.dart';
import 'package:horatio_app/bloc/recording/recording_state.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockRecordingDao extends Mock implements RecordingDao {}

class MockRecordingService extends Mock implements RecordingService {}

class MockAudioPlaybackService extends Mock implements AudioPlaybackService {}

void main() {
  late MockRecordingDao dao;
  late MockRecordingService recordingService;
  late MockAudioPlaybackService playbackService;
  late StreamController<List<LineRecording>> recordingsController;
  late StreamController<PlaybackStatus> statusController;
  late StreamController<Duration> positionController;

  const scriptId = 'script-1';

  final testRecording = LineRecording(
    id: 'r1',
    scriptId: scriptId,
    lineIndex: 0,
    filePath: '/path/to/file.m4a',
    durationMs: 5000,
    createdAt: DateTime.utc(2026),
  );

  setUpAll(() {
    registerFallbackValue(testRecording);
  });

  setUp(() {
    dao = MockRecordingDao();
    recordingService = MockRecordingService();
    playbackService = MockAudioPlaybackService();
    recordingsController = StreamController<List<LineRecording>>.broadcast();
    statusController = StreamController<PlaybackStatus>.broadcast();
    positionController = StreamController<Duration>.broadcast();

    when(() => dao.watchRecordingsForScript(scriptId))
        .thenAnswer((_) => recordingsController.stream);
    when(() => playbackService.status)
        .thenAnswer((_) => statusController.stream);
    when(() => playbackService.position)
        .thenAnswer((_) => positionController.stream);
    when(() => recordingService.dispose()).thenAnswer((_) async {});
    when(() => playbackService.dispose()).thenAnswer((_) async {});
  });

  tearDown(() async {
    await recordingsController.close();
    await statusController.close();
    await positionController.close();
  });

  RecordingCubit createCubit() => RecordingCubit(
        dao: dao,
        recordingService: recordingService,
        playbackService: playbackService,
        recordingsDir: '/tmp/test_recordings',
      );

  group('RecordingCubit', () {
    test('initial state is RecordingInitial', () {
      final cubit = createCubit();
      expect(cubit.state, isA<RecordingInitial>());
      cubit.close();
    });

    test('loadRecordings emits RecordingIdle on stream data', () async {
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      expect(cubit.state, isA<RecordingIdle>());
      expect((cubit.state as RecordingIdle).recordings, [testRecording]);
      await cubit.close();
    });

    test('startRecording transitions to RecordingInProgress', () async {
      when(() => recordingService.hasPermission())
          .thenAnswer((_) async => true);
      when(() => recordingService.startRecording(any()))
          .thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.startRecording(scriptId, 0);

      expect(cubit.state, isA<RecordingInProgress>());
      expect((cubit.state as RecordingInProgress).lineIndex, 0);
      await cubit.close();
    });

    test('recording timer updates elapsed while in progress', () async {
      when(() => recordingService.hasPermission())
          .thenAnswer((_) async => true);
      when(() => recordingService.startRecording(any()))
          .thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.startRecording(scriptId, 0);
      await Future<void>.delayed(const Duration(milliseconds: 120));

      final state = cubit.state;
      expect(state, isA<RecordingInProgress>());
      expect((state as RecordingInProgress).elapsed, isNot(Duration.zero));
      await cubit.close();
    });

    test('startRecording emits error on permission denied', () async {
      when(() => recordingService.hasPermission())
          .thenAnswer((_) async => false);
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.startRecording(scriptId, 0);

      expect(cubit.state, isA<RecordingError>());
      expect(
        (cubit.state as RecordingError).message,
        'Microphone permission required for recording',
      );
      await cubit.close();
    });

    test('startRecording is no-op when already recording', () async {
      when(() => recordingService.hasPermission())
          .thenAnswer((_) async => true);
      when(() => recordingService.startRecording(any()))
          .thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.startRecording(scriptId, 0);
      await cubit.startRecording(scriptId, 1);

      expect((cubit.state as RecordingInProgress).lineIndex, 0);
      verify(() => recordingService.startRecording(any())).called(1);
      await cubit.close();
    });

    test('stopRecording transitions to RecordingIdle', () async {
      when(() => recordingService.hasPermission())
          .thenAnswer((_) async => true);
      when(() => recordingService.startRecording(any()))
          .thenAnswer((_) async {});
      when(() => recordingService.stopRecording())
          .thenAnswer((_) async => '/path/to/file.m4a');
      when(() => dao.insertRecording(any(), any()))
          .thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.startRecording(scriptId, 0);
      await cubit.stopRecording();

      verify(() => dao.insertRecording(scriptId, any())).called(1);
      expect(cubit.state, isA<RecordingIdle>());
      await cubit.close();
    });

    test('stopRecording handles null path', () async {
      when(() => recordingService.hasPermission())
          .thenAnswer((_) async => true);
      when(() => recordingService.startRecording(any()))
          .thenAnswer((_) async {});
      when(() => recordingService.stopRecording())
          .thenAnswer((_) async => null);
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.startRecording(scriptId, 0);
      await cubit.stopRecording();

      verifyNever(() => dao.insertRecording(any(), any()));
      expect(cubit.state, isA<RecordingIdle>());
      await cubit.close();
    });

    test('playRecording transitions to RecordingPlayback', () async {
      when(() => playbackService.play(any())).thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      await cubit.playRecording(testRecording);

      expect(cubit.state, isA<RecordingPlayback>());
      await cubit.close();
    });

    test('playback completion transitions to RecordingGrading', () async {
      when(() => playbackService.play(any())).thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      await cubit.playRecording(testRecording);
      statusController.add(PlaybackStatus.completed);
      await Future<void>.delayed(Duration.zero);

      expect(cubit.state, isA<RecordingGrading>());
      await cubit.close();
    });

    test('stopPlayback transitions to RecordingIdle', () async {
      when(() => playbackService.play(any())).thenAnswer((_) async {});
      when(() => playbackService.stop()).thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      await cubit.playRecording(testRecording);
      await cubit.stopPlayback();

      expect(cubit.state, isA<RecordingIdle>());
      await cubit.close();
    });

    test('gradeRecording calls dao and returns to idle', () async {
      when(() => dao.updateRecordingGrade('r1', 4))
          .thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      await cubit.gradeRecording('r1', 4);

      verify(() => dao.updateRecordingGrade('r1', 4)).called(1);
      expect(cubit.state, isA<RecordingIdle>());
      await cubit.close();
    });

    test('deleteRecording calls dao', () async {
      when(() => dao.deleteRecording('r1')).thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      await cubit.deleteRecording('r1');

      verify(() => dao.deleteRecording('r1')).called(1);
      await cubit.close();
    });

    test('close cancels subscriptions and timer and disposes services',
        () async {
      when(() => recordingService.hasPermission())
          .thenAnswer((_) async => true);
      when(() => recordingService.startRecording(any()))
          .thenAnswer((_) async {});

      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);
      await cubit.startRecording(scriptId, 0);

      await cubit.close();

      verify(() => recordingService.dispose()).called(1);
      verify(() => playbackService.dispose()).called(1);
    });

    test('startRecording is no-op when not in loaded state', () async {
      final cubit = createCubit();

      await cubit.startRecording(scriptId, 0);

      expect(cubit.state, isA<RecordingInitial>());
      await cubit.close();
    });

    test('stopRecording is no-op when not recording', () async {
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.stopRecording();

      expect(cubit.state, isA<RecordingIdle>());
      await cubit.close();
    });

    test('position stream updates RecordingPlayback position', () async {
      when(() => playbackService.play(any())).thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      await cubit.playRecording(testRecording);
      positionController.add(const Duration(seconds: 2));
      await Future<void>.delayed(Duration.zero);

      final state = cubit.state;
      expect(state, isA<RecordingPlayback>());
      expect(
        (state as RecordingPlayback).position,
        const Duration(seconds: 2),
      );
      await cubit.close();
    });

    test('loadRecordings keeps error state while updating recordings',
        () async {
      when(() => recordingService.hasPermission())
          .thenAnswer((_) async => false);
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.startRecording(scriptId, 0);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      final state = cubit.state;
      expect(state, isA<RecordingError>());
      expect((state as RecordingError).recordings, [testRecording]);
      await cubit.close();
    });

    test('loadRecordings keeps in-progress state while updating recordings',
        () async {
      when(() => recordingService.hasPermission())
          .thenAnswer((_) async => true);
      when(() => recordingService.startRecording(any()))
          .thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.startRecording(scriptId, 0);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      final state = cubit.state;
      expect(state, isA<RecordingInProgress>());
      expect((state as RecordingInProgress).recordings, [testRecording]);
      await cubit.close();
    });

    test('loadRecordings keeps playback state while updating recordings',
        () async {
      when(() => playbackService.play(any())).thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      await cubit.playRecording(testRecording);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      expect(cubit.state, isA<RecordingPlayback>());
      await cubit.close();
    });

    test('loadRecordings keeps grading state while updating recordings',
        () async {
      when(() => playbackService.play(any())).thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      await cubit.playRecording(testRecording);
      statusController.add(PlaybackStatus.completed);
      await Future<void>.delayed(Duration.zero);
      recordingsController.add([testRecording]);
      await Future<void>.delayed(Duration.zero);

      expect(cubit.state, isA<RecordingGrading>());
      await cubit.close();
    });

    test('RecordingState equality', () {
      const initial = RecordingInitial();
      expect(initial.recordings, isEmpty);
      expect(initial.props, isEmpty);
      expect(initial, const RecordingInitial());
      expect(
        RecordingIdle(recordings: [testRecording]),
        RecordingIdle(recordings: [testRecording]),
      );
    });
  });
}
