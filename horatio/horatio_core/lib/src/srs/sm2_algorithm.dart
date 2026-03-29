import 'package:horatio_core/src/models/srs_card.dart';
import 'package:horatio_core/src/srs/review_result.dart';

/// Implementation of the SM-2 spaced repetition algorithm.
///
/// Based on the SuperMemo SM-2 algorithm by Piotr Wozniak.
/// See: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
final class Sm2Algorithm {
  /// Creates an [Sm2Algorithm].
  const Sm2Algorithm();

  /// Minimum ease factor to prevent cards from becoming unlearnable.
  static const double minEaseFactor = 1.3;

  /// Processes a [review] and updates the [card] scheduling in place.
  ///
  /// Returns the updated card for convenience (same reference).
  SrsCard processReview({required SrsCard card, required ReviewResult review}) {
    final q = review.quality.value;

    if (review.quality.isCorrect) {
      // Successful recall: increase interval.
      switch (card.repetitions) {
        case 0:
          card.interval = 1;
        case 1:
          card.interval = 6;
        default:
          card.interval = (card.interval * card.easeFactor).round();
      }
      card.repetitions++;
    } else {
      // Failed recall: reset to beginning.
      card
        ..repetitions = 0
        ..interval = 1;
    }

    // Update ease factor using SM-2 formula.
    // EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    final newEase = card.easeFactor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02));
    card
      ..easeFactor = newEase < minEaseFactor ? minEaseFactor : newEase
      ..nextReview = review.reviewedAt.add(Duration(days: card.interval));

    return card;
  }
}
