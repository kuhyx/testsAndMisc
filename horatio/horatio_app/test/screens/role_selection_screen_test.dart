import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/screens/role_selection_screen.dart';
import 'package:horatio_core/horatio_core.dart';

Script _testScript() {
  const hamlet = Role(name: 'Hamlet');
  const horatio = Role(name: 'Horatio');
  return const Script(
    id: 'role-select-test-id',
    title: 'Test Play',
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

Widget _wrapWithRouter(Script script) {
  final router = GoRouter(
    initialLocation: '/role-selection',
    routes: [
      GoRoute(
        path: '/role-selection',
        builder: (context, state) =>
            RoleSelectionScreen(script: script),
      ),
      GoRoute(
        path: '/rehearsal',
        builder: (context, state) =>
            const Scaffold(body: Text('Rehearsal')),
      ),
      GoRoute(
        path: '/schedule',
        builder: (context, state) =>
            const Scaffold(body: Text('Schedule')),
      ),
      GoRoute(
        path: '/annotations',
        builder: (context, state) =>
            const Scaffold(body: Text('Annotations')),
      ),
    ],
  );
  return MaterialApp.router(routerConfig: router);
}

void main() {
  group('RoleSelectionScreen', () {
    testWidgets('shows all roles with line counts', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(
        MaterialApp(home: RoleSelectionScreen(script: script)),
      );

      expect(find.text('Choose Your Role'), findsOneWidget);
      expect(find.text('Test Play'), findsOneWidget);
      expect(find.text('Hamlet'), findsOneWidget);
      expect(find.text('Horatio'), findsOneWidget);
      expect(find.text('2 lines'), findsOneWidget); // Hamlet
      expect(find.text('1 lines'), findsOneWidget); // Horatio
      expect(find.text('1 scenes · 3 lines total'), findsOneWidget);
    });

    testWidgets('shows circle avatar with first letter', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(
        MaterialApp(home: RoleSelectionScreen(script: script)),
      );

      expect(find.text('H'), findsNWidgets(2)); // Hamlet, Horatio
    });

    testWidgets('tapping role opens bottom sheet', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_wrapWithRouter(script));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Hamlet'));
      await tester.pumpAndSettle();

      expect(find.text('Practice "Hamlet"'), findsOneWidget);
      expect(find.text('Rehearsal Mode'), findsOneWidget);
      expect(find.text('Memorization Schedule'), findsOneWidget);
    });

    testWidgets('bottom sheet Rehearsal Mode navigates', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_wrapWithRouter(script));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Hamlet'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Rehearsal Mode'));
      await tester.pumpAndSettle();

      expect(find.text('Rehearsal'), findsOneWidget);
    });

    testWidgets('bottom sheet Memorization Schedule navigates',
        (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_wrapWithRouter(script));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Hamlet'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Memorization Schedule'));
      await tester.pumpAndSettle();

      expect(find.text('Schedule'), findsOneWidget);
    });

    testWidgets('handles role with empty name', (tester) async {
      const emptyRole = Role(name: '');
      const script = Script(
        id: 'edge-id',
        title: 'Edge',
        roles: [emptyRole],
        scenes: [
          Scene(
            lines: [
              ScriptLine(
                text: 'Hello.',
                role: emptyRole,
                sceneIndex: 0,
                lineIndex: 0,
              ),
            ],
          ),
        ],
      );
      await tester.pumpWidget(
        const MaterialApp(home: RoleSelectionScreen(script: script)),
      );

      expect(find.text('?'), findsOneWidget);
    });

    testWidgets('bottom sheet shows Annotate Script option', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_wrapWithRouter(script));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Hamlet'));
      await tester.pumpAndSettle();

      expect(find.text('Annotate Script'), findsOneWidget);
      expect(
        find.text('Add delivery marks and notes'),
        findsOneWidget,
      );
    });

    testWidgets('bottom sheet Annotate Script navigates', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_wrapWithRouter(script));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Hamlet'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Annotate Script'));
      await tester.pumpAndSettle();

      expect(find.text('Annotations'), findsOneWidget);
    });
  });
}
