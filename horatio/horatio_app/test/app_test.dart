import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/app.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  testWidgets('HoratioApp builds without crashing', (tester) async {
    await tester.pumpWidget(const HoratioApp());
    await tester.pumpAndSettle();

    // The app should render the home screen.
    expect(find.text('Horatio'), findsOneWidget);
  });

  testWidgets('SrsReviewCubit is created when srs-review route is visited',
      (tester) async {
    await tester.pumpWidget(const HoratioApp());
    await tester.pumpAndSettle();

    unawaited(appRouter.push(RoutePaths.srsReview, extra: <SrsCard>[
      SrsCard(id: 'c1', cueText: 'Cue', answerText: 'Ans'),
    ]));
    await tester.pumpAndSettle();

    // SrsReviewScreen renders — the BlocProvider.create ran.
    expect(find.text('No review session active.'), findsOneWidget);
  });
}
