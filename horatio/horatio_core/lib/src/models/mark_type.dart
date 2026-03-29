/// Types of text-level delivery marks an actor can place on script text.
enum MarkType {
  /// Stress / emphasize this word.
  stress,

  /// Pause before this span.
  pause,

  /// Take a breath here.
  breath,

  /// General emphasis.
  emphasis,

  /// Deliver this span slower.
  slowDown,

  /// Deliver this span faster.
  speedUp,
}
