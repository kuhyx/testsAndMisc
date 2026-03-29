/// A stage direction extracted from a script.
final class StageDirection {
  /// Creates a [StageDirection] with the given [text].
  const StageDirection({required this.text});

  /// The stage direction text, e.g., "(exits stage left)".
  final String text;

  @override
  String toString() => 'StageDirection($text)';
}
