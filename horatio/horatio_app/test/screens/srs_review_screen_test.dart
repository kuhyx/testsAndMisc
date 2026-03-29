import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_cubit.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_state.dart';
import 'package:horatio_app/screens/srs_review_screen.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockSrsReviewCubit extends MockCubit<SrsReviewState>
    implements SrsReviewCubit {}

List<SrsCard> _makeCards(int count) => List.generate(
      count,
      (i) => SrsCard(
        id: 'card-$i',
        cueText: 'Cue line $i',
        answerText: 'Answer line $i',
      ),
    );

Widget _wrap(SrsReviewCubit cubit, List<SrsCard> cards) =>
    MaterialApp(
      home: BlocProvider<SrsReviewCubit>.value(
        value: cubit,
        child: SrsReviewScreen(cards: cards),
      ),
    );

void main() {
  late MockSrsReviewCubit cubit;

  setUp(() {
    cubit = MockSrsReviewCubit();
  });

  group('SrsReviewScreen', () {
    testWidgets('shows idle message when no session', (tester) async {
      when(() => cubit.state).thenReturn(const SrsReviewIdle());
      await tester.pumpWidget(_wrap(cubit, _makeCards(2)));
      expect(find.text('No review session active.'), findsOneWidget);
    });

    testWidgets('shows card in progress with hidden answer', (tester) async {
      final cards = _makeCards(2);
      when(() => cubit.state).thenReturn(
        SrsReviewInProgress(
          card: cards[0],
          cardIndex: 0,
          totalCards: 2,
          showingAnswer: false,
        ),
      );

      await tester.pumpWidget(_wrap(cubit, cards));

      expect(find.text('Card 1 of 2'), findsOneWidget);
      expect(find.text('CUE'), findsOneWidget);
      expect(find.text('Cue line 0'), findsOneWidget);
      expect(find.text('Show Answer'), findsOneWidget);
      // Answer text should NOT be shown.
      expect(find.text('YOUR LINE'), findsNothing);
    });

    testWidgets('tapping Show Answer calls cubit.showAnswer', (tester) async {
      final cards = _makeCards(1);
      when(() => cubit.state).thenReturn(
        SrsReviewInProgress(
          card: cards[0],
          cardIndex: 0,
          totalCards: 1,
          showingAnswer: false,
        ),
      );

      await tester.pumpWidget(_wrap(cubit, cards));
      await tester.tap(find.text('Show Answer'));

      verify(() => cubit.showAnswer()).called(1);
    });

    testWidgets('shows answer and grade buttons when revealed',
        (tester) async {
      final cards = _makeCards(1);
      when(() => cubit.state).thenReturn(
        SrsReviewInProgress(
          card: cards[0],
          cardIndex: 0,
          totalCards: 1,
          showingAnswer: true,
        ),
      );

      await tester.pumpWidget(_wrap(cubit, cards));

      expect(find.text('YOUR LINE'), findsOneWidget);
      expect(find.text('Answer line 0'), findsOneWidget);
      expect(find.text('Again'), findsOneWidget);
      expect(find.text('Hard'), findsOneWidget);
      expect(find.text('Good'), findsOneWidget);
      expect(find.text('Easy'), findsOneWidget);
    });

    testWidgets('tapping grade buttons calls cubit.gradeCard',
        (tester) async {
      final cards = _makeCards(1);
      when(() => cubit.state).thenReturn(
        SrsReviewInProgress(
          card: cards[0],
          cardIndex: 0,
          totalCards: 1,
          showingAnswer: true,
        ),
      );

      await tester.pumpWidget(_wrap(cubit, cards));
      await tester.tap(find.text('Easy'));

      verify(() => cubit.gradeCard(ReviewQuality.perfect)).called(1);
    });

    testWidgets('shows done view with accuracy', (tester) async {
      when(() => cubit.state).thenReturn(
        const SrsReviewDone(totalReviewed: 10, correctCount: 7),
      );

      await tester.pumpWidget(_wrap(cubit, _makeCards(10)));

      expect(find.text('Review Complete!'), findsOneWidget);
      expect(find.text('7/10 correct (70%)'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
    });

    testWidgets('shows 0% accuracy when no cards reviewed', (tester) async {
      when(() => cubit.state).thenReturn(
        const SrsReviewDone(totalReviewed: 0, correctCount: 0),
      );

      await tester.pumpWidget(_wrap(cubit, []));

      expect(find.text('0/0 correct (0%)'), findsOneWidget);
    });

    testWidgets('Done button in complete view pops the route',
        (tester) async {
      when(() => cubit.state).thenReturn(
        const SrsReviewDone(totalReviewed: 5, correctCount: 3),
      );

      // Use a nested navigator so pop() has somewhere to return.
      await tester.pumpWidget(MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: ElevatedButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => BlocProvider<SrsReviewCubit>.value(
                    value: cubit,
                    child: const SrsReviewScreen(cards: []),
                  ),
                ),
              ),
              child: const Text('Go'),
            ),
          ),
        ),
      ));

      await tester.tap(find.text('Go'));
      await tester.pumpAndSettle();

      expect(find.text('Done'), findsOneWidget);
      await tester.tap(find.text('Done'));
      await tester.pumpAndSettle();

      // Should be back on the first screen.
      expect(find.text('Go'), findsOneWidget);
    });
  });
}
