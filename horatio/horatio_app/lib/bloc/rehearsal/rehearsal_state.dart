import 'package:equatable/equatable.dart';
import 'package:horatio_core/horatio_core.dart';

/// State for [RehearsalCubit].
sealed class RehearsalState extends Equatable {
  const RehearsalState();
}

/// Rehearsal not started yet.
final class RehearsalInitial extends RehearsalState {
  const RehearsalInitial();

  @override
  List<Object?> get props => [];
}

/// Waiting for the actor to say their line.
final class RehearsalAwaitingLine extends RehearsalState {
  const RehearsalAwaitingLine({
    required this.cueText,
    required this.cueSpeaker,
    required this.expectedLine,
    required this.lineIndex,
    required this.totalLines,
  });

  /// The cue line text shown/spoken to the actor.
  final String cueText;

  /// Who speaks the cue.
  final String cueSpeaker;

  /// The line the actor should recite.
  final String expectedLine;

  /// Current line index in the session.
  final int lineIndex;

  /// Total lines in this rehearsal session.
  final int totalLines;

  @override
  List<Object?> get props => [
        cueText,
        cueSpeaker,
        expectedLine,
        lineIndex,
        totalLines,
      ];
}

/// The actor has submitted their line and can see feedback.
final class RehearsalFeedback extends RehearsalState {
  const RehearsalFeedback({
    required this.expectedLine,
    required this.actualLine,
    required this.grade,
    required this.diffSegments,
    required this.lineIndex,
    required this.totalLines,
  });

  /// The expected line text.
  final String expectedLine;

  /// What the actor typed/said.
  final String actualLine;

  /// Match quality grade.
  final LineMatchGrade grade;

  /// Word-level diff for highlighting.
  final List<DiffSegment> diffSegments;

  /// Current line index.
  final int lineIndex;

  /// Total lines.
  final int totalLines;

  @override
  List<Object?> get props => [
        expectedLine,
        actualLine,
        grade,
        diffSegments,
        lineIndex,
        totalLines,
      ];
}

/// Rehearsal session completed.
final class RehearsalComplete extends RehearsalState {
  const RehearsalComplete({
    required this.totalLines,
    required this.exactCount,
    required this.minorCount,
    required this.majorCount,
    required this.missedCount,
  });

  /// Total lines rehearsed.
  final int totalLines;

  /// Lines graded as exact.
  final int exactCount;

  /// Lines graded as minor deviations.
  final int minorCount;

  /// Lines graded as major deviations.
  final int majorCount;

  /// Lines missed.
  final int missedCount;

  @override
  List<Object?> get props => [
        totalLines,
        exactCount,
        minorCount,
        majorCount,
        missedCount,
      ];
}
