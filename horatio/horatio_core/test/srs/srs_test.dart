import 'package:horatio_core/horatio_core.dart';
import 'package:test/test.dart';

void main() {
  group('Sm2Algorithm', () {
    const algorithm = Sm2Algorithm();

    SrsCard makeCard() => SrsCard(
      id: 'test_card',
      cueText: 'To be, or not to be',
      answerText: 'That is the question',
    );

    ReviewResult makeReview({required ReviewQuality quality, DateTime? at}) =>
        ReviewResult(
          cardId: 'test_card',
          quality: quality,
          reviewedAt: at ?? DateTime(2026, 3, 28),
        );

    test('first correct review sets interval to 1', () {
      final card = makeCard();
      algorithm.processReview(
        card: card,
        review: makeReview(quality: ReviewQuality.perfect),
      );
      expect(card.interval, 1);
      expect(card.repetitions, 1);
    });

    test('second correct review sets interval to 6', () {
      final card = makeCard()..repetitions = 1;
      algorithm.processReview(
        card: card,
        review: makeReview(quality: ReviewQuality.perfect),
      );
      expect(card.interval, 6);
      expect(card.repetitions, 2);
    });

    test('third correct review uses ease factor', () {
      final card = makeCard()
        ..repetitions = 2
        ..interval = 6;
      algorithm.processReview(
        card: card,
        review: makeReview(quality: ReviewQuality.perfect),
      );
      // 6 * 2.5 = 15
      expect(card.interval, 15);
      expect(card.repetitions, 3);
    });

    test('failed review resets repetitions and interval', () {
      final card = makeCard()
        ..repetitions = 5
        ..interval = 30;
      algorithm.processReview(
        card: card,
        review: makeReview(quality: ReviewQuality.blackout),
      );
      expect(card.interval, 1);
      expect(card.repetitions, 0);
    });

    test('ease factor increases on perfect response', () {
      final card = makeCard();
      final initialEase = card.easeFactor;
      algorithm.processReview(
        card: card,
        review: makeReview(quality: ReviewQuality.perfect),
      );
      expect(card.easeFactor, greaterThan(initialEase));
    });

    test('ease factor decreases on difficult response', () {
      final card = makeCard();
      final initialEase = card.easeFactor;
      algorithm.processReview(
        card: card,
        review: makeReview(quality: ReviewQuality.correctDifficult),
      );
      expect(card.easeFactor, lessThan(initialEase));
    });

    test('ease factor never drops below 1.3', () {
      final card = makeCard()..easeFactor = 1.3;
      algorithm.processReview(
        card: card,
        review: makeReview(quality: ReviewQuality.blackout),
      );
      expect(card.easeFactor, greaterThanOrEqualTo(1.3));
    });

    test('schedules next review based on interval', () {
      final card = makeCard();
      final reviewDate = DateTime(2026, 3, 28);
      algorithm.processReview(
        card: card,
        review: makeReview(quality: ReviewQuality.perfect, at: reviewDate),
      );
      expect(card.nextReview, DateTime(2026, 3, 29)); // 1 day later
    });

    test('ReviewQuality.isCorrect threshold', () {
      expect(ReviewQuality.blackout.isCorrect, isFalse);
      expect(ReviewQuality.incorrect.isCorrect, isFalse);
      expect(ReviewQuality.incorrectButRecognized.isCorrect, isFalse);
      expect(ReviewQuality.correctDifficult.isCorrect, isTrue);
      expect(ReviewQuality.correctHesitation.isCorrect, isTrue);
      expect(ReviewQuality.perfect.isCorrect, isTrue);
    });
  });

  group('CardScheduler', () {
    const scheduler = CardScheduler();

    List<SrsCard> makeCards(int count) => List.generate(
      count,
      (i) => SrsCard(id: 'card_$i', cueText: 'Cue $i', answerText: 'Answer $i'),
    );

    test('getDueCards returns cards due on or before date', () {
      final cards = makeCards(3);
      // Card 0: due today, Card 1: due tomorrow, Card 2: due yesterday.
      final today = DateTime(2026, 3, 28);
      cards[0].nextReview = today;
      cards[1].nextReview = today.add(const Duration(days: 1));
      cards[2].nextReview = today.subtract(const Duration(days: 1));

      final due = scheduler.getDueCards(allCards: cards, date: today);
      expect(due, hasLength(2));
      expect(due.map((c) => c.id), containsAll(['card_0', 'card_2']));
    });

    test('getNewCards returns unreviewed cards', () {
      final cards = makeCards(3);
      cards[0].repetitions = 1; // Been reviewed.
      final newCards = scheduler.getNewCards(allCards: cards);
      expect(newCards, hasLength(2));
    });

    test('newCardsPerDay distributes across available days', () {
      final perDay = scheduler.newCardsPerDay(
        totalNewCards: 100,
        deadline: DateTime(2026, 4, 7),
        startDate: DateTime(2026, 3, 28),
      );
      // Distributes 100 cards over available days.
      expect(perDay, greaterThan(0));
      expect(perDay, lessThanOrEqualTo(20));
    });

    test('newCardsPerDay returns all cards if deadline passed', () {
      final perDay = scheduler.newCardsPerDay(
        totalNewCards: 50,
        deadline: DateTime(2026, 3, 27),
        startDate: DateTime(2026, 3, 28),
      );
      expect(perDay, 50);
    });

    test('newCardsPerDay defaults startDate to now', () {
      final perDay = scheduler.newCardsPerDay(
        totalNewCards: 100,
        deadline: DateTime(2099),
      );
      expect(perDay, greaterThan(0));
    });

    test('getTodaySession combines due and new cards', () {
      final cards = makeCards(5);
      final today = DateTime(2026, 3, 28);
      // Cards 0-1 are due (reviewed before).
      cards[0]
        ..repetitions = 1
        ..nextReview = today.subtract(const Duration(days: 1));
      cards[1]
        ..repetitions = 1
        ..nextReview = today;
      // Cards 2-4 are new.

      final session = scheduler.getTodaySession(
        allCards: cards,
        maxNewCards: 2,
        today: today,
      );
      // 2 due + 2 new = 4
      expect(session, hasLength(4));
    });

    test('getTodaySession defaults today to now', () {
      final cards = makeCards(3);
      // Make cards not yet due (far future review date).
      for (final card in cards) {
        card.nextReview = DateTime(2099);
      }

      final session = scheduler.getTodaySession(
        allCards: cards,
        maxNewCards: 2,
      );
      // 0 due + 2 new = 2
      expect(session, hasLength(2));
    });
  });
}
