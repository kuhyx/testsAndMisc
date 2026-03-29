import 'dart:async';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/recording/recording_state.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/services/audio_playback_service.dart';
import 'package:horatio_app/services/recording_service.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:uuid/uuid.dart';

/// Manages the record -> play -> grade lifecycle for voice recordings.
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
    bool disposeServicesOnClose = true,
  }) : _dao = dao,
       _recordingService = recordingService,
       _playbackService = playbackService,
       _recordingsDir = recordingsDir,
       _disposeServicesOnClose = disposeServicesOnClose,
       super(const RecordingInitial());

  final RecordingDao _dao;
  final RecordingService _recordingService;
  final AudioPlaybackService _playbackService;
  final String _recordingsDir;
  final bool _disposeServicesOnClose;

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
    _recordingsSub = _dao.watchRecordingsForScript(scriptId).listen((
      recordings,
    ) {
      _latestRecordings = recordings;
      final current = state;
      if (current is RecordingInProgress) {
        emit(
          RecordingInProgress(
            recordings: recordings,
            lineIndex: current.lineIndex,
            elapsed: current.elapsed,
          ),
        );
      } else if (current is RecordingPlayback) {
        emit(
          RecordingPlayback(
            recordings: recordings,
            recording: current.recording,
            position: current.position,
          ),
        );
      } else if (current is RecordingGrading) {
        emit(
          RecordingGrading(
            recordings: recordings,
            recording: current.recording,
          ),
        );
      } else if (current is RecordingError) {
        emit(RecordingError(recordings: recordings, message: current.message));
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
      emit(
        RecordingError(
          recordings: _latestRecordings,
          message: 'Microphone permission required for recording',
        ),
      );
      return;
    }

    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final filePath =
        '$_recordingsDir/$scriptId/line_${lineIndex}_$timestamp.m4a';

    await _recordingService.startRecording(filePath);
    _recordingLineIndex = lineIndex;
    _recordingStartedAt = DateTime.now();

    var elapsed = Duration.zero;
    emit(
      RecordingInProgress(
        recordings: _latestRecordings,
        lineIndex: lineIndex,
        elapsed: elapsed,
      ),
    );

    _elapsedTimer?.cancel();
    _elapsedTimer = Timer.periodic(const Duration(milliseconds: 100), (_) {
      elapsed += const Duration(milliseconds: 100);
      if (state is RecordingInProgress) {
        emit(
          RecordingInProgress(
            recordings: _latestRecordings,
            lineIndex: lineIndex,
            elapsed: elapsed,
          ),
        );
      }
    });
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

    final scriptId = _scriptId!;
    final lineIndex = _recordingLineIndex!;

    final elapsed = _recordingStartedAt != null
        ? DateTime.now().difference(_recordingStartedAt!)
        : Duration.zero;

    final recording = LineRecording(
      id: _uuid.v4(),
      scriptId: scriptId,
      lineIndex: lineIndex,
      filePath: path,
      durationMs: elapsed.inMilliseconds,
      createdAt: DateTime.now().toUtc(),
    );

    await _dao.insertRecording(scriptId, recording);
    emit(RecordingIdle(recordings: _latestRecordings));
  }

  /// Plays a recording.
  Future<void> playRecording(LineRecording recording) async {
    await _playbackService.play(recording.filePath);
    emit(
      RecordingPlayback(
        recordings: _latestRecordings,
        recording: recording,
        position: Duration.zero,
      ),
    );

    await _positionSub?.cancel();
    _positionSub = _playbackService.position.listen((position) {
      if (state is RecordingPlayback) {
        emit(
          RecordingPlayback(
            recordings: _latestRecordings,
            recording: recording,
            position: position,
          ),
        );
      }
    });

    await _statusSub?.cancel();
    _statusSub = _playbackService.status.listen((status) {
      if (status == PlaybackStatus.completed && state is RecordingPlayback) {
        unawaited(_positionSub?.cancel());
        unawaited(_statusSub?.cancel());
        emit(
          RecordingGrading(recordings: _latestRecordings, recording: recording),
        );
      }
    });
  }

  /// Stops playback.
  Future<void> stopPlayback() async {
    await _playbackService.stop();
    await _positionSub?.cancel();
    await _statusSub?.cancel();
    emit(RecordingIdle(recordings: _latestRecordings));
  }

  /// Grades a recording (0-5).
  Future<void> gradeRecording(String id, int grade) async {
    await _dao.updateRecordingGrade(id, grade);
    emit(RecordingIdle(recordings: _latestRecordings));
  }

  /// Deletes a recording.
  Future<void> deleteRecording(String id) => _dao.deleteRecording(id);

  @override
  Future<void> close() async {
    await _recordingsSub?.cancel();
    await _statusSub?.cancel();
    await _positionSub?.cancel();
    _elapsedTimer?.cancel();
    if (_disposeServicesOnClose) {
      await _recordingService.dispose();
      await _playbackService.dispose();
    }
    return super.close();
  }
}
