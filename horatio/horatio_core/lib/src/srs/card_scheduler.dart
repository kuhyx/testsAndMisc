import 'package:horatio_core/src/models/srs_card.dart';

/// Schedules daily SRS review sessions based on available cards and deadline.
final class CardScheduler {
  /// Creates a [CardScheduler].
  const CardScheduler();

  /// Returns all cards that are due for review on or before [date].
  List<SrsCard> getDueCards({
    required List<SrsCard> allCards,
    required DateTime date,
  }) => allCards.where((card) => card.isDue(now: date)).toList();

  /// Returns cards that have never been reviewed (new cards).
  List<SrsCard> getNewCards({required List<SrsCard> allCards}) =>
      allCards.where((card) => card.isNew).toList();

  /// Calculates how many new cards to introduce per day given
  /// a [deadline] and [totalNewCards].
  ///
  /// Returns the number of new cards per day, minimum 1.
  int newCardsPerDay({
    required int totalNewCards,
    required DateTime deadline,
    DateTime? startDate,
  }) {
    final start = startDate ?? DateTime.now();
    final daysRemaining = deadline.difference(start).inDays;
    if (daysRemaining <= 0) return totalNewCards;
    final perDay = (totalNewCards / daysRemaining).ceil();
    return perDay < 1 ? 1 : perDay;
  }

  /// Selects the cards for today's session: due reviews + new cards.
  ///
  /// [maxNewCards] limits how many new cards to introduce in this session.
  List<SrsCard> getTodaySession({
    required List<SrsCard> allCards,
    required int maxNewCards,
    DateTime? today,
  }) {
    final now = today ?? DateTime.now();
    final dueCards = getDueCards(allCards: allCards, date: now);
    final newCards = getNewCards(allCards: allCards);

    // Take up to maxNewCards new cards.
    final newForToday = newCards.take(maxNewCards).toList();

    // Combine: reviews first, then new cards.
    return [...dueCards, ...newForToday];
  }
}
