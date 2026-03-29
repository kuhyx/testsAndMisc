import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/rehearsal/rehearsal_state.dart';
import 'package:horatio_core/horatio_core.dart';

/// Manages dialogue rehearsal flow.
class RehearsalCubit extends Cubit<RehearsalState> {
  /// Creates a [RehearsalCubit] for running a dialogue session.
  RehearsalCubit({
    required Script script,
    required Role selectedRole,
  })  : _comparator = const LineComparator(),
        _grades = [],
        super(const RehearsalInitial()) {
    _buildDialogueSequence(script, selectedRole);
  }

  final LineComparator _comparator;

  /// Pairs of (cueLine, actorLine) for the session.
  final List<_DialoguePair> _pairs = [];
  int _currentIndex = 0;
  final List<LineMatchGrade> _grades;

  void _buildDialogueSequence(Script script, Role selectedRole) {
    for (final scene in script.scenes) {
      for (var i = 0; i < scene.lines.length; i++) {
        final line = scene.lines[i];
        if (line.role == selectedRole && i > 0) {
          // Find the previous non-stage-direction line as cue.
          final cue = _findCue(scene.lines, i);
          if (cue != null) {
            _pairs.add(
              _DialoguePair(
                cueText: cue.text,
                cueSpeaker: cue.role?.name ?? 'Stage Direction',
                expectedLine: line.text,
              ),
            );
          }
        }
      }
    }
  }

  ScriptLine? _findCue(List<ScriptLine> lines, int beforeIndex) {
    for (var i = beforeIndex - 1; i >= 0; i--) {
      if (!lines[i].isStageDirection) return lines[i];
    }
    return null;
  }

  /// Starts the rehearsal session at the first line.
  void start() {
    if (_pairs.isEmpty) {
      emit(
        const RehearsalComplete(
          totalLines: 0,
          exactCount: 0,
          minorCount: 0,
          majorCount: 0,
          missedCount: 0,
        ),
      );
      return;
    }
    _currentIndex = 0;
    _grades.clear();
    _emitAwaiting();
  }

  /// Submits the actor's [response] for the current line.
  void submitLine(String response) {
    if (_currentIndex >= _pairs.length) return;

    final pair = _pairs[_currentIndex];
    final grade = _comparator.grade(pair.expectedLine, response);
    final segments = _comparator.wordDiff(pair.expectedLine, response);

    _grades.add(grade);
    emit(
      RehearsalFeedback(
        expectedLine: pair.expectedLine,
        actualLine: response,
        grade: grade,
        diffSegments: segments,
        lineIndex: _currentIndex,
        totalLines: _pairs.length,
      ),
    );
  }

  /// Advances to the next line after viewing feedback.
  void nextLine() {
    _currentIndex++;
    if (_currentIndex >= _pairs.length) {
      _emitComplete();
    } else {
      _emitAwaiting();
    }
  }

  void _emitAwaiting() {
    final pair = _pairs[_currentIndex];
    emit(
      RehearsalAwaitingLine(
        cueText: pair.cueText,
        cueSpeaker: pair.cueSpeaker,
        expectedLine: pair.expectedLine,
        lineIndex: _currentIndex,
        totalLines: _pairs.length,
      ),
    );
  }

  void _emitComplete() {
    var exact = 0;
    var minor = 0;
    var major = 0;
    var missed = 0;

    for (final g in _grades) {
      switch (g) {
        case LineMatchGrade.exact:
          exact++;
        case LineMatchGrade.minor:
          minor++;
        case LineMatchGrade.major:
          major++;
        case LineMatchGrade.missed:
          missed++;
      }
    }

    emit(
      RehearsalComplete(
        totalLines: _pairs.length,
        exactCount: exact,
        minorCount: minor,
        majorCount: major,
        missedCount: missed,
      ),
    );
  }
}

/// Internal pair of cue + expected actor line.
final class _DialoguePair {
  const _DialoguePair({
    required this.cueText,
    required this.cueSpeaker,
    required this.expectedLine,
  });

  final String cueText;
  final String cueSpeaker;
  final String expectedLine;
}
