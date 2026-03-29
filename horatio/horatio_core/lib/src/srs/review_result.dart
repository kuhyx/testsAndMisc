/// Quality rating for an SRS review, using the SM-2 scale (0–5).
enum ReviewQuality {
  /// Complete blackout — no recall at all.
  blackout(0),

  /// Incorrect, but the correct answer seemed easy to recall once shown.
  incorrect(1),

  /// Incorrect, but the correct answer was recognized.
  incorrectButRecognized(2),

  /// Correct, but with serious difficulty.
  correctDifficult(3),

  /// Correct, after hesitation.
  correctHesitation(4),

  /// Perfect response with no hesitation.
  perfect(5);

  const ReviewQuality(this.value);

  /// Numeric SM-2 quality value (0–5).
  final int value;

  /// Whether this response counts as a successful recall.
  bool get isCorrect => value >= 3;
}

/// The result of reviewing an SRS card.
final class ReviewResult {
  /// Creates a [ReviewResult].
  const ReviewResult({
    required this.cardId,
    required this.quality,
    required this.reviewedAt,
  });

  /// The ID of the card that was reviewed.
  final String cardId;

  /// The quality of the actor's response.
  final ReviewQuality quality;

  /// When the review took place.
  final DateTime reviewedAt;
}
