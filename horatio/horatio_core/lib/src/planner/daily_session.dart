/// A planned daily rehearsal session.
final class DailySession {
  /// Creates a [DailySession].
  const DailySession({
    required this.date,
    required this.newCardCount,
    required this.reviewCardCount,
  });

  /// The date of this session.
  final DateTime date;

  /// Number of new cards to introduce.
  final int newCardCount;

  /// Estimated number of review cards due.
  final int reviewCardCount;

  /// Total cards for this session.
  int get totalCards => newCardCount + reviewCardCount;

  @override
  String toString() =>
      'DailySession(${date.toIso8601String().split('T').first}'
      ', new: $newCardCount, review: $reviewCardCount)';
}
