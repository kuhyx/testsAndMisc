import 'package:equatable/equatable.dart';
import 'package:horatio_core/horatio_core.dart';

/// State for [SrsReviewCubit].
sealed class SrsReviewState extends Equatable {
  const SrsReviewState();
}

/// No review session active.
final class SrsReviewIdle extends SrsReviewState {
  const SrsReviewIdle();

  @override
  List<Object?> get props => [];
}

/// Showing a card for review.
final class SrsReviewInProgress extends SrsReviewState {
  const SrsReviewInProgress({
    required this.card,
    required this.cardIndex,
    required this.totalCards,
    required this.showingAnswer,
  });

  /// The current card being reviewed.
  final SrsCard card;

  /// Index in the session.
  final int cardIndex;

  /// Total cards in this session.
  final int totalCards;

  /// Whether the answer is currently revealed.
  final bool showingAnswer;

  @override
  List<Object?> get props => [card.id, cardIndex, totalCards, showingAnswer];
}

/// Review session finished.
final class SrsReviewDone extends SrsReviewState {
  const SrsReviewDone({
    required this.totalReviewed,
    required this.correctCount,
  });

  /// Total cards reviewed.
  final int totalReviewed;

  /// Cards graded correctly (quality >= 3).
  final int correctCount;

  @override
  List<Object?> get props => [totalReviewed, correctCount];
}
