import 'package:horatio_core/src/models/role.dart';
import 'package:horatio_core/src/models/stage_direction.dart';

/// A single line of dialogue or stage direction in a script.
final class ScriptLine {
  /// Creates a [ScriptLine] for dialogue.
  const ScriptLine({
    required this.text,
    required this.role,
    required this.sceneIndex,
    required this.lineIndex,
    this.stageDirection,
  });

  /// Creates a [ScriptLine] that is purely a stage direction.
  const ScriptLine.direction({
    required this.text,
    required this.sceneIndex,
    required this.lineIndex,
  }) : role = null,
       stageDirection = null;

  /// The dialogue text. For stage directions without dialogue, this holds
  /// the direction text.
  final String text;

  /// The character speaking, or `null` for pure stage directions.
  final Role? role;

  /// Zero-based index of the scene this line belongs to.
  final int sceneIndex;

  /// Zero-based position of this line within the overall script.
  final int lineIndex;

  /// Optional stage direction associated with this line.
  final StageDirection? stageDirection;

  /// Whether this line is a stage direction (no speaker).
  bool get isStageDirection => role == null;

  @override
  String toString() {
    final speaker = role?.name ?? 'DIRECTION';
    return 'ScriptLine($speaker: ${text.length > 40 ? '${text.substring(0, 40)}...' : text})';
  }
}
