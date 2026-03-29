import 'package:equatable/equatable.dart';
import 'package:horatio_core/horatio_core.dart';

/// States for [RecordingCubit].
sealed class RecordingState extends Equatable {
  const RecordingState();

  /// All recordings for the current script.
  ///
  /// Empty in [RecordingInitial], populated after
  /// [RecordingCubit.loadRecordings].
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
  @override
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
  @override
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
  @override
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
  @override
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
  @override
  final List<LineRecording> recordings;

  /// Error message.
  final String message;

  @override
  List<Object?> get props => [recordings, message];
}
