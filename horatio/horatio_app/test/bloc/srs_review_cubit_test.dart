import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_cubit.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_state.dart';
import 'package:horatio_core/horatio_core.dart';

List<SrsCard> _makeCards(int count) => List.generate(
      count,
      (i) => SrsCard(
        id: 'card-$i',
        cueText: 'Cue $i',
        answerText: 'Answer $i',
      ),
    );

void main() {
  group('SrsReviewCubit', () {
    blocTest<SrsReviewCubit, SrsReviewState>(
      'initial state is SrsReviewIdle',
      build: SrsReviewCubit.new,
      verify: (cubit) => expect(cubit.state, isA<SrsReviewIdle>()),
    );

    blocTest<SrsReviewCubit, SrsReviewState>(
      'startSession with empty list emits Done',
      build: SrsReviewCubit.new,
      act: (cubit) => cubit.startSession([]),
      expect: () => [
        isA<SrsReviewDone>()
            .having((s) => s.totalReviewed, 'totalReviewed', 0)
            .having((s) => s.correctCount, 'correctCount', 0),
      ],
    );

    blocTest<SrsReviewCubit, SrsReviewState>(
      'startSession with cards emits InProgress for first card',
      build: SrsReviewCubit.new,
      act: (cubit) => cubit.startSession(_makeCards(3)),
      expect: () => [
        isA<SrsReviewInProgress>()
            .having((s) => s.cardIndex, 'cardIndex', 0)
            .having((s) => s.totalCards, 'totalCards', 3)
            .having((s) => s.showingAnswer, 'showingAnswer', false),
      ],
    );

    blocTest<SrsReviewCubit, SrsReviewState>(
      'showAnswer reveals answer',
      build: SrsReviewCubit.new,
      act: (cubit) {
        cubit
          ..startSession(_makeCards(2))
          ..showAnswer();
      },
      expect: () => [
        isA<SrsReviewInProgress>()
            .having((s) => s.showingAnswer, 'hidden', false),
        isA<SrsReviewInProgress>()
            .having((s) => s.showingAnswer, 'shown', true),
      ],
    );

    blocTest<SrsReviewCubit, SrsReviewState>(
      'showAnswer is no-op when not in progress',
      build: SrsReviewCubit.new,
      act: (cubit) => cubit.showAnswer(),
      expect: () => <SrsReviewState>[],
    );

    blocTest<SrsReviewCubit, SrsReviewState>(
      'gradeCard advances to next card',
      build: SrsReviewCubit.new,
      act: (cubit) {
        cubit
          ..startSession(_makeCards(2))
          ..gradeCard(ReviewQuality.perfect);
      },
      expect: () => [
        isA<SrsReviewInProgress>().having((s) => s.cardIndex, 'idx', 0),
        isA<SrsReviewInProgress>().having((s) => s.cardIndex, 'idx', 1),
      ],
    );

    blocTest<SrsReviewCubit, SrsReviewState>(
      'gradeCard on last card emits Done with correct counts',
      build: SrsReviewCubit.new,
      act: (cubit) {
        cubit
          ..startSession(_makeCards(2))
          ..gradeCard(ReviewQuality.perfect) // correct
          ..gradeCard(ReviewQuality.blackout); // incorrect
      },
      expect: () => [
        isA<SrsReviewInProgress>(),
        isA<SrsReviewInProgress>(),
        isA<SrsReviewDone>()
            .having((s) => s.totalReviewed, 'total', 2)
            .having((s) => s.correctCount, 'correct', 1),
      ],
    );

    blocTest<SrsReviewCubit, SrsReviewState>(
      'gradeCard is no-op after session ends',
      build: SrsReviewCubit.new,
      act: (cubit) {
        cubit
          ..startSession(_makeCards(1))
          ..gradeCard(ReviewQuality.perfect)
          ..gradeCard(ReviewQuality.perfect); // should be ignored
      },
      expect: () => [
        isA<SrsReviewInProgress>(),
        isA<SrsReviewDone>(),
      ],
    );

    test('state classes have correct Equatable props', () {
      const idle = SrsReviewIdle();
      expect(idle.props, isEmpty);

      final inProgress = SrsReviewInProgress(
        card: _makeCards(1).first,
        cardIndex: 0,
        totalCards: 1,
        showingAnswer: false,
      );
      expect(inProgress.props, hasLength(4));

      const done = SrsReviewDone(totalReviewed: 5, correctCount: 3);
      expect(done.props, hasLength(2));
    });
  });
}
