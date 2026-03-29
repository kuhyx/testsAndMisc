import 'dart:async';

import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/script_import/script_import_cubit.dart';
import 'package:horatio_app/bloc/script_import/script_import_state.dart';
import 'package:horatio_app/screens/import_screen.dart';
import 'package:horatio_app/services/script_repository.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockScriptImportCubit extends MockCubit<ScriptImportState>
    implements ScriptImportCubit {}

Widget _wrap(ScriptImportCubit cubit) {
  final repo = ScriptRepository();
  return MultiRepositoryProvider(
    providers: [
      RepositoryProvider<ScriptRepository>(create: (_) => repo),
    ],
    child: BlocProvider<ScriptImportCubit>.value(
      value: cubit,
      child: const MaterialApp(home: ImportScreen()),
    ),
  );
}

Widget _wrapWithRouter(ScriptImportCubit cubit) {
  final repo = ScriptRepository();
  final router = GoRouter(
    initialLocation: '/import',
    routes: [
      GoRoute(
        path: '/import',
        builder: (context, state) => const ImportScreen(),
      ),
      GoRoute(
        path: '/role-selection',
        builder: (context, state) =>
            const Scaffold(body: Text('RoleSelection')),
      ),
    ],
  );
  return MultiRepositoryProvider(
    providers: [
      RepositoryProvider<ScriptRepository>(create: (_) => repo),
    ],
    child: BlocProvider<ScriptImportCubit>.value(
      value: cubit,
      child: MaterialApp.router(routerConfig: router),
    ),
  );
}

void main() {
  late MockScriptImportCubit cubit;

  setUp(() {
    cubit = MockScriptImportCubit();
    when(() => cubit.state).thenReturn(const ScriptImportInitial());
    when(() => cubit.importFromFile()).thenAnswer((_) async {});
    when(() => cubit.importFromText(
          text: any(named: 'text'),
          title: any(named: 'title'),
        )).thenAnswer((_) async {});
  });

  group('ImportScreen', () {
    testWidgets('shows two tabs', (tester) async {
      await tester.pumpWidget(_wrap(cubit));

      expect(find.text('Import Script'), findsOneWidget);
      expect(find.text('From File'), findsOneWidget);
      expect(find.text('Paste Text'), findsOneWidget);
    });

    testWidgets('File tab has Choose File button', (tester) async {
      await tester.pumpWidget(_wrap(cubit));

      expect(find.text('Choose File'), findsOneWidget);
    });

    testWidgets('tapping Choose File calls importFromFile', (tester) async {
      await tester.pumpWidget(_wrap(cubit));

      await tester.tap(find.text('Choose File'));
      await tester.pump();

      verify(() => cubit.importFromFile()).called(1);
    });

    testWidgets('Paste Text tab has form fields', (tester) async {
      await tester.pumpWidget(_wrap(cubit));

      // Switch to paste tab.
      await tester.tap(find.text('Paste Text'));
      await tester.pumpAndSettle();

      expect(find.text('Script Title'), findsOneWidget);
      expect(find.text('Script Text'), findsOneWidget);
      expect(find.text('Import'), findsOneWidget);
    });

    testWidgets('shows snackbar when fields are empty on import',
        (tester) async {
      await tester.pumpWidget(_wrap(cubit));

      await tester.tap(find.text('Paste Text'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Import'));
      await tester.pumpAndSettle();

      expect(
        find.text('Title and script text are required.'),
        findsOneWidget,
      );
    });

    testWidgets('calls importFromText with filled fields', (tester) async {
      await tester.pumpWidget(_wrap(cubit));

      await tester.tap(find.text('Paste Text'));
      await tester.pumpAndSettle();

      await tester.enterText(
        find.widgetWithText(TextField, 'Script Title'),
        'My Script',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'Script Text'),
        'ROMEO: Hello.\nJULIET: Hi.',
      );
      await tester.tap(find.text('Import'));
      await tester.pump();

      verify(
        () => cubit.importFromText(
          text: 'ROMEO: Hello.\nJULIET: Hi.',
          title: 'My Script',
        ),
      ).called(1);
    });

    testWidgets('BlocListener shows error snackbar', (tester) async {
      final stateController =
          StreamController<ScriptImportState>.broadcast();

      whenListen(
        cubit,
        stateController.stream,
        initialState: const ScriptImportInitial(),
      );

      await tester.pumpWidget(_wrap(cubit));

      stateController.add(const ScriptImportError(message: 'Parse failed'));
      await tester.pumpAndSettle();

      expect(find.text('Parse failed'), findsOneWidget);

      await stateController.close();
    });

    testWidgets(
        'BlocListener navigates to role-selection on successful import',
        (tester) async {
      final stateController =
          StreamController<ScriptImportState>.broadcast();

      whenListen(
        cubit,
        stateController.stream,
        initialState: const ScriptImportInitial(),
      );

      await tester.pumpWidget(_wrapWithRouter(cubit));

      // Emit a loaded state with a script.
      const role = Role(name: 'Actor');
      const script = Script(
        id: 'import-test-id',
        title: 'Test',
        roles: [role],
        scenes: [
          Scene(
            lines: [
              ScriptLine(
                text: 'Hello.',
                role: role,
                sceneIndex: 0,
                lineIndex: 0,
              ),
            ],
          ),
        ],
      );
      stateController.add(const ScriptImportLoaded(scripts: [script]));
      await tester.pumpAndSettle();

      // Should have navigated to role-selection.
      expect(find.text('RoleSelection'), findsOneWidget);

      await stateController.close();
    });
  });
}
