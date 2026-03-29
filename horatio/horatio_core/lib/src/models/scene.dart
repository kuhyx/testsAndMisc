import 'package:horatio_core/src/models/script_line.dart';

/// A scene within a script, containing an ordered list of lines.
final class Scene {
  /// Creates a [Scene] with an optional [title] and its [lines].
  const Scene({required this.lines, this.title = '', this.index = 0});

  /// Optional scene title (e.g., "Act I, Scene 2").
  final String title;

  /// Zero-based index of this scene within the script.
  final int index;

  /// Ordered lines of dialogue and stage directions in this scene.
  final List<ScriptLine> lines;

  @override
  String toString() =>
      'Scene(${title.isEmpty ? 'untitled' : title}, ${lines.length} lines)';
}
