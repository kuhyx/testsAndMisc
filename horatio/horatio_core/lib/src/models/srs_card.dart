/// An SRS flashcard for memorization using the SM-2 algorithm.
final class SrsCard {
  /// Creates a new [SrsCard] for a line/cue pair.
  SrsCard({
    required this.id,
    required this.cueText,
    required this.answerText,
    this.interval = 1,
    this.repetitions = 0,
    this.easeFactor = 2.5,
    DateTime? nextReview,
  }) : nextReview = nextReview ?? DateTime.now();

  /// Unique identifier for this card.
  final String id;

  /// The cue shown to the actor (preceding line or prompt).
  final String cueText;

  /// The text the actor must recall.
  final String answerText;

  /// Days until next review.
  int interval;

  /// Number of consecutive correct reviews.
  int repetitions;

  /// SM-2 ease factor (minimum 1.3).
  double easeFactor;

  /// When this card is next due for review.
  DateTime nextReview;

  /// Whether this card is due for review.
  bool isDue({DateTime? now}) {
    final currentTime = now ?? DateTime.now();
    return !currentTime.isBefore(nextReview);
  }

  /// Whether this card has never been reviewed.
  bool get isNew => repetitions == 0;

  @override
  String toString() =>
      'SrsCard($id, interval: $interval, '
      'ease: ${easeFactor.toStringAsFixed(2)})';
}
