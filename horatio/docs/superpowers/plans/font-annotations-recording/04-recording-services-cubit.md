## Chunk 4: Recording Services + Cubit

### Task 4.1: RecordingService

**Files:**

- Create: `horatio_app/lib/services/recording_service.dart`
- Create: `horatio_app/test/services/recording_service_test.dart`

- [ ] **Step 1: Write failing tests**

RecordingService wraps the `record` package. Tests must fully mock it.

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:mocktail/mocktail.dart';
import 'package:record/record.dart';

class MockAudioRecorder extends Mock implements AudioRecorder {}

void main() {
  late MockAudioRecorder mockRecorder;
  late RecordingService service;

  setUp(() {
    mockRecorder = MockAudioRecorder();
    service = RecordingService(recorder: mockRecorder);
  });

  tearDown(() => service.dispose());

  group('RecordingService', () {
    test('startRecording starts recording to path', () async {
      when(() => mockRecorder.start(any(), path: any(named: 'path')))
          .thenAnswer((_) async {});
      when(() => mockRecorder.hasPermission())
          .thenAnswer((_) async => true);
      await service.startRecording('/tmp/test.m4a');
      verify(
        () => mockRecorder.start(
          any(),
          path: '/tmp/test.m4a',
        ),
      ).called(1);
    });

    test('stopRecording stops and returns path', () async {
      when(() => mockRecorder.stop()).thenAnswer((_) async => '/tmp/test.m4a');
      final path = await service.stopRecording();
      expect(path, '/tmp/test.m4a');
    });

    test('hasPermission delegates', () async {
      when(() => mockRecorder.hasPermission())
          .thenAnswer((_) async => true);
      expect(await service.hasPermission(), isTrue);
    });

    test('hasPermission returns false', () async {
      when(() => mockRecorder.hasPermission())
          .thenAnswer((_) async => false);
      expect(await service.hasPermission(), isFalse);
    });

    test('dispose calls recorder dispose', () async {
      when(() => mockRecorder.dispose()).thenAnswer((_) async {});
      await service.dispose();
      verify(() => mockRecorder.dispose()).called(1);
    });
  });
}
```

- [ ] **Step 2: Implement RecordingService**

```dart
import 'package:record/record.dart';

/// Wraps the [AudioRecorder] for microphone recording.
class RecordingService {
  /// Creates a [RecordingService].
  RecordingService({AudioRecorder? recorder})
      : _recorder = recorder ?? AudioRecorder();

  final AudioRecorder _recorder;

  /// Whether the app has microphone permission.
  Future<bool> hasPermission() => _recorder.hasPermission();

  /// Starts recording to the given file path.
  Future<void> startRecording(String filePath) async {
    await _recorder.start(const RecordConfig(), path: filePath);
  }

  /// Stops recording and returns the file path.
  Future<String?> stopRecording() => _recorder.stop();

  /// Releases the recorder resources.
  Future<void> dispose() => _recorder.dispose();
}
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/services/recording_service_test.dart -v
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/services/recording_service.dart horatio_app/test/services/recording_service_test.dart
git commit -m "feat(recording): add RecordingService wrapper for record package"
```

---

### Task 4.2: AudioPlaybackService

**Files:**

- Create: `horatio_app/lib/services/audio_playback_service.dart`
- Create: `horatio_app/test/services/audio_playback_service_test.dart`

- [ ] **Step 1: Write failing tests**

```dart
import 'dart:async';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:mocktail/mocktail.dart';

class MockAudioPlayer extends Mock implements AudioPlayer {}

void main() {
  late MockAudioPlayer mockPlayer;
  late AudioPlaybackService service;

  setUp(() {
    mockPlayer = MockAudioPlayer();
    service = AudioPlaybackService(player: mockPlayer);
    when(() => mockPlayer.onPlayerStateChanged)
        .thenAnswer((_) => const Stream.empty());
    when(() => mockPlayer.onPositionChanged)
        .thenAnswer((_) => const Stream.empty());
  });

  tearDown(() async {
    when(() => mockPlayer.dispose()).thenAnswer((_) async {});
    await service.dispose();
  });

  setUpAll(() {
    registerFallbackValue(DeviceFileSource(''));
  });

  group('AudioPlaybackService', () {
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

      controller.add(PlayerState.playing);
      controller.add(PlayerState.completed);
      controller.add(PlayerState.stopped);
      controller.add(PlayerState.paused);

      await Future<void>.delayed(Duration.zero);
      expect(statuses, [
        PlaybackStatus.playing,
        PlaybackStatus.completed,
        PlaybackStatus.idle,
        PlaybackStatus.idle,
      ]);

      await sub.cancel();
      await controller.close();
      when(() => mockPlayer.dispose()).thenAnswer((_) async {});
      await service2.dispose();
    });

    test('position stream delegates', () async {
      final controller = StreamController<Duration>();
      when(() => mockPlayer.onPositionChanged)
          .thenAnswer((_) => controller.stream);
      final service2 = AudioPlaybackService(player: mockPlayer);

      final positions = <Duration>[];
      final sub = service2.position.listen(positions.add);

      controller.add(const Duration(seconds: 1));
      controller.add(const Duration(seconds: 2));

      await Future<void>.delayed(Duration.zero);
      expect(positions, [
        const Duration(seconds: 1),
        const Duration(seconds: 2),
      ]);

      await sub.cancel();
      await controller.close();
      when(() => mockPlayer.dispose()).thenAnswer((_) async {});
      await service2.dispose();
    });

    test('dispose calls player.dispose', () async {
      when(() => mockPlayer.dispose()).thenAnswer((_) async {});
      await service.dispose();
      verify(() => mockPlayer.dispose()).called(1);
    });
  });
}
```

- [ ] **Step 2: Implement AudioPlaybackService**

```dart
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
      : _player = player ?? AudioPlayer();

  final AudioPlayer _player;

  /// Plays audio from a local file path.
  Future<void> play(String filePath) =>
      _player.play(DeviceFileSource(filePath));

  /// Stops playback.
  Future<void> stop() => _player.stop();

  /// Stream of playback status changes.
  Stream<PlaybackStatus> get status =>
      _player.onPlayerStateChanged.map((state) => switch (state) {
            PlayerState.playing => PlaybackStatus.playing,
            PlayerState.completed => PlaybackStatus.completed,
            _ => PlaybackStatus.idle,
          });

  /// Stream of playback position.
  Stream<Duration> get position => _player.onPositionChanged;

  /// Releases the player resources.
  Future<void> dispose() => _player.dispose();
}
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/services/audio_playback_service_test.dart -v
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/services/audio_playback_service.dart horatio_app/test/services/audio_playback_service_test.dart
git commit -m "feat(recording): add AudioPlaybackService with status stream"
```

---

### Task 4.3: RecordingState

**Files:**

- Create: `horatio_app/lib/bloc/recording/recording_state.dart`

- [ ] **Step 1: Create state file**

```dart
import 'package:equatable/equatable.dart';
import 'package:horatio_core/horatio_core.dart';

/// States for [RecordingCubit].
sealed class RecordingState extends Equatable {
  const RecordingState();

  /// All recordings for the current script.
  /// Empty in [RecordingInitial], populated after [RecordingCubit.loadRecordings].
  List<LineRecording> get recordings;
}

/// No recordings loaded.
final class RecordingInitial extends RecordingState {
  const RecordingInitial();

  @override
  List<LineRecording> get recordings => const [];

  @override
  List<Object?> get props => [];
}

/// Idle — recordings loaded, nothing in progress.
final class RecordingIdle extends RecordingState {
  const RecordingIdle({required this.recordings});

  /// All recordings for the current script.
  final List<LineRecording> recordings;

  @override
  List<Object?> get props => [recordings];
}

/// Recording in progress.
final class RecordingInProgress extends RecordingState {
  const RecordingInProgress({
    required this.recordings,
    required this.lineIndex,
    required this.elapsed,
  });

  /// All recordings for the current script.
  final List<LineRecording> recordings;

  /// The line being recorded.
  final int lineIndex;

  /// Elapsed recording time.
  final Duration elapsed;

  @override
  List<Object?> get props => [recordings, lineIndex, elapsed];
}

/// Playing back a recording.
final class RecordingPlayback extends RecordingState {
  const RecordingPlayback({
    required this.recordings,
    required this.recording,
    required this.position,
  });

  /// All recordings for the current script.
  final List<LineRecording> recordings;

  /// The recording being played.
  final LineRecording recording;

  /// Current playback position.
  final Duration position;

  @override
  List<Object?> get props => [recordings, recording, position];
}

/// Grading a recording after playback.
final class RecordingGrading extends RecordingState {
  const RecordingGrading({
    required this.recordings,
    required this.recording,
  });

  /// All recordings for the current script.
  final List<LineRecording> recordings;

  /// The recording to grade.
  final LineRecording recording;

  @override
  List<Object?> get props => [recordings, recording];
}

/// Error state.
final class RecordingError extends RecordingState {
  const RecordingError({
    required this.recordings,
    required this.message,
  });

  /// All recordings for the current script.
  final List<LineRecording> recordings;

  /// Error message.
  final String message;

  @override
  List<Object?> get props => [recordings, message];
}
```

- [ ] **Step 2: Commit**

```bash
git add horatio_app/lib/bloc/recording/recording_state.dart
git commit -m "feat(recording): add RecordingState hierarchy"
```

---

### Task 4.4: RecordingCubit

**Files:**

- Create: `horatio_app/lib/bloc/recording/recording_cubit.dart`
- Create: `horatio_app/test/bloc/recording_cubit_test.dart`

- [ ] **Step 1: Write failing tests**

This is the most complex test file. Key branches to cover:

```dart
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
  });

  tearDown(() {
    recordingsController.close();
    statusController.close();
    positionController.close();
  });

  setUpAll(() {
    registerFallbackValue(testRecording);
  });

  RecordingCubit createCubit() => RecordingCubit(
        dao: dao,
        recordingService: recordingService,
        playbackService: playbackService,
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
      await cubit.startRecording(scriptId, 1); // Should be ignored.
      expect((cubit.state as RecordingInProgress).lineIndex, 0);
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

    test('close cancels stream subscriptions and timer', () async {
      when(() => recordingService.hasPermission())
          .thenAnswer((_) async => true);
      when(() => recordingService.startRecording(any()))
          .thenAnswer((_) async {});
      final cubit = createCubit()..loadRecordings(scriptId);
      recordingsController.add([]);
      await Future<void>.delayed(Duration.zero);
      await cubit.startRecording(scriptId, 0);
      await cubit.close();
      // No errors from timer after close.
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
      await cubit.stopRecording(); // Should not throw.
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
      expect((state as RecordingPlayback).position,
          const Duration(seconds: 2));
      await cubit.close();
    });

    test('RecordingState equality', () {
      expect(const RecordingInitial(), const RecordingInitial());
      expect(
        RecordingIdle(recordings: [testRecording]),
        RecordingIdle(recordings: [testRecording]),
      );
    });
  });
}
```

- [ ] **Step 2: Implement RecordingCubit**

Key design choices:

- Recording file path is generated by `RecordingService` (not the cubit) to avoid `dart:io` dependency in the cubit. Pass the `recordingsDir` (from `path_provider`) through the constructor.
- The cubit never touches the filesystem directly — all I/O goes through `RecordingService`.

```dart
import 'dart:async';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/recording/recording_state.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:uuid/uuid.dart';

/// Manages the record → play → grade lifecycle for voice recordings.
class RecordingCubit extends Cubit<RecordingState> {
  /// Creates a [RecordingCubit].
  ///
  /// [recordingsDir] is the base directory for storing recordings
  /// (from path_provider's getApplicationDocumentsDirectory).
  RecordingCubit({
    required RecordingDao dao,
    required RecordingService recordingService,
    required AudioPlaybackService playbackService,
    required String recordingsDir,
  })  : _dao = dao,
        _recordingService = recordingService,
        _playbackService = playbackService,
        _recordingsDir = recordingsDir,
        super(const RecordingInitial());

  final RecordingDao _dao;
  final RecordingService _recordingService;
  final AudioPlaybackService _playbackService;
  final String _recordingsDir;

  static const _uuid = Uuid();

  StreamSubscription<List<LineRecording>>? _recordingsSub;
  StreamSubscription<PlaybackStatus>? _statusSub;
  StreamSubscription<Duration>? _positionSub;
  Timer? _elapsedTimer;

  String? _scriptId;
  int? _recordingLineIndex;
  DateTime? _recordingStartedAt;
  List<LineRecording> _latestRecordings = [];

  /// Subscribes to recording streams for a script.
  void loadRecordings(String scriptId) {
    _scriptId = scriptId;
    _recordingsSub?.cancel();
    _recordingsSub =
        _dao.watchRecordingsForScript(scriptId).listen((recordings) {
      _latestRecordings = recordings;
      final current = state;
      if (current is RecordingInProgress) {
        emit(RecordingInProgress(
          recordings: recordings,
          lineIndex: current.lineIndex,
          elapsed: current.elapsed,
        ));
      } else if (current is RecordingPlayback) {
        emit(RecordingPlayback(
          recordings: recordings,
          recording: current.recording,
          position: current.position,
        ));
      } else if (current is RecordingGrading) {
        emit(RecordingGrading(
          recordings: recordings,
          recording: current.recording,
        ));
      } else if (current is RecordingError) {
        emit(RecordingError(
          recordings: recordings,
          message: current.message,
        ));
      } else {
        emit(RecordingIdle(recordings: recordings));
      }
    });
  }

  /// Starts recording for a line.
  Future<void> startRecording(String scriptId, int lineIndex) async {
    if (state is RecordingInProgress) return;
    if (state is RecordingInitial) return;

    final hasPermission = await _recordingService.hasPermission();
    if (!hasPermission) {
      emit(RecordingError(
        recordings: _latestRecordings,
        message: 'Microphone permission required for recording',
      ));
      return;
    }

    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final filePath =
        '$_recordingsDir/$scriptId/line_${lineIndex}_$timestamp.m4a';

    await _recordingService.startRecording(filePath);
    _recordingLineIndex = lineIndex;
    _recordingStartedAt = DateTime.now();

    var elapsed = Duration.zero;
    emit(RecordingInProgress(
      recordings: _latestRecordings,
      lineIndex: lineIndex,
      elapsed: elapsed,
    ));

    _elapsedTimer = Timer.periodic(
      const Duration(milliseconds: 100),
      (_) {
        elapsed += const Duration(milliseconds: 100);
        if (state is RecordingInProgress) {
          emit(RecordingInProgress(
            recordings: _latestRecordings,
            lineIndex: lineIndex,
            elapsed: elapsed,
          ));
        }
      },
    );
  }

  /// Stops recording and saves to database.
  Future<void> stopRecording() async {
    if (state is! RecordingInProgress) return;
    _elapsedTimer?.cancel();
    _elapsedTimer = null;

    final path = await _recordingService.stopRecording();
    if (path == null) {
      emit(RecordingIdle(recordings: _latestRecordings));
      return;
    }

    final elapsed = _recordingStartedAt != null
        ? DateTime.now().difference(_recordingStartedAt!)
        : Duration.zero;

    final recording = LineRecording(
      id: _uuid.v4(),
      scriptId: _scriptId!,
      lineIndex: _recordingLineIndex!,
      filePath: path,
      durationMs: elapsed.inMilliseconds,
      createdAt: DateTime.now().toUtc(),
    );

    await _dao.insertRecording(_scriptId!, recording);
    emit(RecordingIdle(recordings: _latestRecordings));
  }

  /// Plays a recording.
  Future<void> playRecording(LineRecording recording) async {
    await _playbackService.play(recording.filePath);
    emit(RecordingPlayback(
      recordings: _latestRecordings,
      recording: recording,
      position: Duration.zero,
    ));

    _positionSub?.cancel();
    _positionSub = _playbackService.position.listen((position) {
      if (state is RecordingPlayback) {
        emit(RecordingPlayback(
          recordings: _latestRecordings,
          recording: recording,
          position: position,
        ));
      }
    });

    _statusSub?.cancel();
    _statusSub = _playbackService.status.listen((status) {
      if (status == PlaybackStatus.completed && state is RecordingPlayback) {
        _positionSub?.cancel();
        _statusSub?.cancel();
        emit(RecordingGrading(
          recordings: _latestRecordings,
          recording: recording,
        ));
      }
    });
  }

  /// Stops playback.
  Future<void> stopPlayback() async {
    await _playbackService.stop();
    _positionSub?.cancel();
    _statusSub?.cancel();
    emit(RecordingIdle(recordings: _latestRecordings));
  }

  /// Grades a recording (0-5).
  Future<void> gradeRecording(String id, int grade) =>
      _dao.updateRecordingGrade(id, grade);

  /// Deletes a recording.
  Future<void> deleteRecording(String id) => _dao.deleteRecording(id);

  @override
  Future<void> close() {
    _recordingsSub?.cancel();
    _statusSub?.cancel();
    _positionSub?.cancel();
    _elapsedTimer?.cancel();
    return super.close();
  }
}
```

Also update the `RecordingService.startRecording` to create the parent directory. Change the implementation in `recording_service.dart` (from Task 4.1) to:

```dart
import 'dart:io';

import 'package:record/record.dart';

/// Wraps the [AudioRecorder] for microphone recording.
class RecordingService {
  /// Creates a [RecordingService].
  RecordingService({AudioRecorder? recorder})
      : _recorder = recorder ?? AudioRecorder();

  final AudioRecorder _recorder;

  /// Whether the app has microphone permission.
  Future<bool> hasPermission() => _recorder.hasPermission();

  /// Starts recording to the given file path.
  /// Creates the parent directory if it doesn't exist.
  Future<void> startRecording(String filePath) async {
    final dir = Directory(filePath).parent;
    if (!dir.existsSync()) {
      await dir.create(recursive: true);
    }
    await _recorder.start(const RecordConfig(), path: filePath);
  }

  /// Stops recording and returns the file path.
  Future<String?> stopRecording() => _recorder.stop();

  /// Releases the recorder resources.
  Future<void> dispose() => _recorder.dispose();
}
```

Update the `RecordingCubit` test to pass `recordingsDir`:

```dart
RecordingCubit createCubit() => RecordingCubit(
      dao: dao,
      recordingService: recordingService,
      playbackService: playbackService,
      recordingsDir: '/tmp/test_recordings',
    );
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/bloc/recording_cubit_test.dart -v
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add horatio_app/lib/bloc/recording/ horatio_app/test/bloc/recording_cubit_test.dart
git commit -m "feat(recording): add RecordingCubit with full state machine"
```

---

### Task 4.5: Run pipeline for Chunk 4

- [ ] **Step 1: Run codegen + analyze + test**

```bash
cd /home/kuhy/testsAndMisc/horatio && ./run.sh test
```

Expected: 100% coverage.

---
