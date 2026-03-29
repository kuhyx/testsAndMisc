import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/app.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers/test_database.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('HoratioApp builds without crashing', (tester) async {
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(
      HoratioApp(
        database: createTestDatabase(),
        recordingsDir: '/tmp/test_recordings',
        prefs: prefs,
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Horatio'), findsOneWidget);
  });

  testWidgets('SrsReviewCubit is created when srs-review route is visited', (
    tester,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(
      HoratioApp(
        database: createTestDatabase(),
        recordingsDir: '/tmp/test_recordings',
        prefs: prefs,
      ),
    );
    await tester.pumpAndSettle();

    unawaited(
      appRouter.push(
        RoutePaths.srsReview,
        extra: <SrsCard>[SrsCard(id: 'c1', cueText: 'Cue', answerText: 'Ans')],
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('No review session active.'), findsOneWidget);
  });

  testWidgets('AnnotationDao is provided when annotation route is visited', (
    tester,
  ) async {
    final db = createTestDatabase();
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(
      HoratioApp(
        database: db,
        recordingsDir: '/tmp/test_recordings',
        prefs: prefs,
      ),
    );
    await tester.pumpAndSettle();

    const role = Role(name: 'Hero');
    const script = Script(
      id: 'app-ann-id',
      title: 'Ann Test',
      roles: [role],
      scenes: [
        Scene(
          lines: [
            ScriptLine(text: 'Hello.', role: role, sceneIndex: 0, lineIndex: 0),
          ],
        ),
      ],
    );
    unawaited(appRouter.push(RoutePaths.annotations, extra: script));
    await tester.pumpAndSettle();
    expect(find.text('Annotate: Ann Test'), findsOneWidget);

    // Close the database before teardown to cancel Drift stream timers.
    await db.close();
  });
}
