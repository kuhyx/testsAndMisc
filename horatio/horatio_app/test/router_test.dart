import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/script_import/script_import_cubit.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_cubit.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/router.dart';
import 'package:horatio_app/services/script_repository.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class _MockAnnotationDao extends Mock implements AnnotationDao {}

Widget _wrapRouter() {
  final repository = ScriptRepository();
  final mockDao = _MockAnnotationDao();
  when(() => mockDao.watchMarksForScript(any()))
      .thenAnswer((_) => Stream.value([]));
  when(() => mockDao.watchNotesForScript(any()))
      .thenAnswer((_) => Stream.value([]));
  when(() => mockDao.watchSnapshotsForScript(any()))
      .thenAnswer((_) => Stream.value([]));
  return MultiRepositoryProvider(
    providers: [
      RepositoryProvider<ScriptRepository>(create: (_) => repository),
      RepositoryProvider<AnnotationDao>.value(value: mockDao),
    ],
    child: MultiBlocProvider(
      providers: [
        BlocProvider<ScriptImportCubit>(
          create: (_) => ScriptImportCubit(repository: repository),
        ),
        BlocProvider<SrsReviewCubit>(create: (_) => SrsReviewCubit()),
      ],
      child: MaterialApp.router(routerConfig: appRouter),
    ),
  );
}

void main() {
  group('Router with valid extras', () {
    testWidgets('import route shows ImportScreen', (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      appRouter.go(RoutePaths.import_);
      await tester.pumpAndSettle();

      expect(find.text('Import Script'), findsOneWidget);
    });

    testWidgets('role-selection route with Script extra', (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      const role = Role(name: 'Hero');
      const script = Script(
        id: 'router-valid-id',
        title: 'Valid',
        roles: [role],
        scenes: [
          Scene(
            lines: [
              ScriptLine(
                text: 'Line.',
                role: role,
                sceneIndex: 0,
                lineIndex: 0,
              ),
            ],
          ),
        ],
      );

      unawaited(appRouter.push(RoutePaths.roleSelection, extra: script));
      await tester.pumpAndSettle();

      expect(find.text('Choose Your Role'), findsOneWidget);
    });

    testWidgets('schedule route with map extra', (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      const role = Role(name: 'Hero');
      const script = Script(
        id: 'router-play-id',
        title: 'Play',
        roles: [role],
        scenes: [
          Scene(
            lines: [
              ScriptLine(
                text: 'Hi.',
                role: role,
                sceneIndex: 0,
                lineIndex: 0,
              ),
            ],
          ),
        ],
      );

      unawaited(appRouter.push(
        RoutePaths.schedule,
        extra: {'script': script, 'role': role},
      ));
      await tester.pumpAndSettle();

      expect(find.text('Memorization Schedule'), findsOneWidget);
    });

    testWidgets('rehearsal route with map extra', (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      const role = Role(name: 'Hero');
      const script = Script(
        id: 'router-rehearse-id',
        title: 'Rehearse',
        roles: [role],
        scenes: [
          Scene(
            lines: [
              ScriptLine(
                text: 'A.',
                role: role,
                sceneIndex: 0,
                lineIndex: 0,
              ),
            ],
          ),
        ],
      );

      unawaited(appRouter.push(
        RoutePaths.rehearsal,
        extra: {'script': script, 'role': role},
      ));
      await tester.pumpAndSettle();

      expect(find.text('Rehearsing: Hero'), findsOneWidget);
    });

    testWidgets('srs-review route with cards extra', (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      final cards = [
        SrsCard(id: 'c1', cueText: 'Cue', answerText: 'Ans'),
      ];

      unawaited(appRouter.push(RoutePaths.srsReview, extra: cards));
      await tester.pumpAndSettle();

      // SrsReviewScreen is visible.
      expect(find.text('No review session active.'), findsOneWidget);
    });

    testWidgets('error route shows 404', (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      appRouter.go('/nonexistent-route');
      await tester.pumpAndSettle();

      expect(find.text('Not Found'), findsOneWidget);
    });

    testWidgets('schedule route with wrong extra type falls back',
        (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      // Push schedule with a non-Map extra → the builder returns SizedBox.
      unawaited(appRouter.push(RoutePaths.schedule, extra: 'wrong'));
      await tester.pumpAndSettle();

      // Should not crash — shows SizedBox.shrink or redirects.
      expect(tester.takeException(), isNull);
    });

    testWidgets('annotations route with Script extra shows editor',
        (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      // Reset to home to clear any stale navigation stack.
      appRouter.go(RoutePaths.home);
      await tester.pumpAndSettle();

      const role = Role(name: 'Hero');
      const script = Script(
        id: 'router-annotate-id',
        title: 'Annotate Play',
        roles: [role],
        scenes: [
          Scene(
            lines: [
              ScriptLine(
                text: 'Line.',
                role: role,
                sceneIndex: 0,
                lineIndex: 0,
              ),
            ],
          ),
        ],
      );

      unawaited(appRouter.push(RoutePaths.annotations, extra: script));
      await tester.pumpAndSettle();

      expect(find.text('Annotate: Annotate Play'), findsOneWidget);
    });

    testWidgets('annotations route with null extra redirects home',
        (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      appRouter.go(RoutePaths.annotations);
      await tester.pumpAndSettle();

      // Redirected to home.
      expect(find.text('Horatio'), findsOneWidget);
    });

    testWidgets('annotation-history route with Script extra shows history',
        (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      const role = Role(name: 'Hero');
      const script = Script(
        id: 'router-history-id',
        title: 'History Play',
        roles: [role],
        scenes: [
          Scene(
            lines: [
              ScriptLine(
                text: 'Line.',
                role: role,
                sceneIndex: 0,
                lineIndex: 0,
              ),
            ],
          ),
        ],
      );

      unawaited(
        appRouter.push(RoutePaths.annotationHistory, extra: script),
      );
      await tester.pumpAndSettle();

      expect(find.text('History: History Play'), findsOneWidget);
    });

    testWidgets('annotation-history route with null extra redirects home',
        (tester) async {
      await tester.pumpWidget(_wrapRouter());
      await tester.pumpAndSettle();

      appRouter.go(RoutePaths.annotationHistory);
      await tester.pumpAndSettle();

      // Redirected to home.
      expect(find.text('Horatio'), findsOneWidget);
    });
  });
}
