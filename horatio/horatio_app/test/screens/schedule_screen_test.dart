import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/srs_review/srs_review_cubit.dart';
import 'package:horatio_app/screens/schedule_screen.dart';
import 'package:horatio_core/horatio_core.dart';

Widget _wrap(Script script, Role role) {
  final cubit = SrsReviewCubit();
  final router = GoRouter(
    initialLocation: '/schedule',
    routes: [
      GoRoute(
        path: '/schedule',
        builder: (context, state) =>
            ScheduleScreen(script: script, selectedRole: role),
      ),
      GoRoute(
        path: '/srs-review',
        builder: (context, state) => const Scaffold(),
      ),
    ],
  );
  return BlocProvider<SrsReviewCubit>.value(
    value: cubit,
    child: MaterialApp.router(routerConfig: router),
  );
}

Script _testScript() {
  const hamlet = Role(name: 'Hamlet');
  const horatio = Role(name: 'Horatio');
  return const Script(
    title: 'Test',
    roles: [hamlet, horatio],
    scenes: [
      Scene(
        lines: [
          ScriptLine(
            text: 'To be.',
            role: hamlet,
            sceneIndex: 0,
            lineIndex: 0,
          ),
          ScriptLine(
            text: 'Indeed.',
            role: horatio,
            sceneIndex: 0,
            lineIndex: 1,
          ),
          ScriptLine(
            text: 'Well then.',
            role: hamlet,
            sceneIndex: 0,
            lineIndex: 2,
          ),
        ],
      ),
    ],
  );
}

void main() {
  group('ScheduleScreen', () {
    testWidgets('shows summary card and daily plan', (tester) async {
      final script = _testScript();
      final role = script.roles.first;
      await tester.pumpWidget(_wrap(script, role));

      expect(find.text('Memorization Schedule'), findsOneWidget);
      expect(find.text('Hamlet'), findsOneWidget);
      expect(find.text('Daily Plan'), findsOneWidget);
      expect(find.text('Start Review'), findsOneWidget);
      // Summary shows card count.
      expect(find.textContaining('cards to memorize'), findsOneWidget);
      expect(find.textContaining('due today'), findsOneWidget);
    });

    testWidgets('shows day entries in list', (tester) async {
      final script = _testScript();
      final role = script.roles.first;
      await tester.pumpWidget(_wrap(script, role));

      expect(find.text('Day 1'), findsOneWidget);
      expect(find.textContaining('new'), findsAtLeastNWidgets(1));
    });

    testWidgets('FAB shows snackbar when no due cards', (tester) async {
      // Create a script where the selected role has no lines.
      const hamlet = Role(name: 'Hamlet');
      const horatio = Role(name: 'Horatio');
      const script = Script(
        title: 'One-sided',
        roles: [hamlet, horatio],
        scenes: [
          Scene(
            lines: [
              ScriptLine(
                text: 'Only Horatio speaks.',
                role: horatio,
                sceneIndex: 0,
                lineIndex: 0,
              ),
            ],
          ),
        ],
      );

      // Select Hamlet who has no lines → 0 cards → dueCards.isEmpty.
      await tester.pumpWidget(_wrap(script, hamlet));

      await tester.tap(find.text('Start Review'));
      await tester.pumpAndSettle();

      expect(
        find.text('No cards due for review today.'),
        findsOneWidget,
      );
    });
    testWidgets('FAB starts review when due cards exist', (tester) async {
      final script = _testScript();
      final role = script.roles.first;
      await tester.pumpWidget(_wrap(script, role));

      await tester.tap(find.text('Start Review'));
      await tester.pumpAndSettle();

      // Should have navigated to /srs-review.
      expect(find.byType(ScheduleScreen), findsNothing);
    });
  });
}
