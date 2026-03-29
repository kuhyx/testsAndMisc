/// Categories for line-level interpretive notes.
enum NoteCategory {
  /// "What does the character want here?"
  intention,

  /// "What are they really saying?"
  subtext,

  /// "Cross downstage on this line."
  blocking,

  /// "Suppressed anger building."
  emotion,

  /// "Whisper this line."
  delivery,

  /// Catch-all for uncategorized notes.
  general,
}
