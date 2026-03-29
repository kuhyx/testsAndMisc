import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_state.dart';
import 'package:horatio_core/horatio_core.dart';

/// Manages SRS flashcard review sessions.
class SrsReviewCubit extends Cubit<SrsReviewState> {
  /// Creates an [SrsReviewCubit].
  SrsReviewCubit() : super(const SrsReviewIdle());

  final Sm2Algorithm _algorithm = const Sm2Algorithm();

  List<SrsCard> _cards = [];
  int _currentIndex = 0;
  int _correctCount = 0;

  /// Starts a review session with the given [cards].
  void startSession(List<SrsCard> cards) {
    _cards = cards;
    _currentIndex = 0;
    _correctCount = 0;

    if (_cards.isEmpty) {
      emit(const SrsReviewDone(totalReviewed: 0, correctCount: 0));
      return;
    }

    _emitCurrent(showingAnswer: false);
  }

  /// Reveals the answer for the current card.
  void showAnswer() {
    if (state is! SrsReviewInProgress) return;
    _emitCurrent(showingAnswer: true);
  }

  /// Grades the current card and advances.
  void gradeCard(ReviewQuality quality) {
    if (_currentIndex >= _cards.length) return;

    final card = _cards[_currentIndex];
    final result = ReviewResult(
      cardId: card.id,
      quality: quality,
      reviewedAt: DateTime.now(),
    );
    _algorithm.processReview(card: card, review: result);

    if (quality.isCorrect) _correctCount++;

    _currentIndex++;
    if (_currentIndex >= _cards.length) {
      emit(
        SrsReviewDone(
          totalReviewed: _cards.length,
          correctCount: _correctCount,
        ),
      );
    } else {
      _emitCurrent(showingAnswer: false);
    }
  }

  void _emitCurrent({required bool showingAnswer}) {
    emit(
      SrsReviewInProgress(
        card: _cards[_currentIndex],
        cardIndex: _currentIndex,
        totalCards: _cards.length,
        showingAnswer: showingAnswer,
      ),
    );
  }
}
