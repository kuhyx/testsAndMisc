import 'dart:typed_data';

import 'package:bloc_test/bloc_test.dart';
import 'package:desktop_drop/desktop_drop.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/bloc/script_import/script_import_cubit.dart';
import 'package:horatio_app/bloc/script_import/script_import_state.dart';
import 'package:horatio_app/screens/home_screen.dart';
import 'package:horatio_app/services/script_repository.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockScriptImportCubit extends MockCubit<ScriptImportState>
    implements ScriptImportCubit {}

Widget _wrap(ScriptImportCubit cubit) {
  final router = GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/role-selection',
        builder: (context, state) => const Scaffold(),
      ),
    ],
  );
  return MultiRepositoryProvider(
    providers: [
      RepositoryProvider<ScriptRepository>(
        create: (_) => ScriptRepository(),
      ),
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
    when(() => cubit.loadScripts()).thenReturn(null);
    when(() => cubit.importFromFile()).thenAnswer((_) async {});
    when(() => cubit.importFromAsset(any())).thenAnswer((_) async {});
    when(() => cubit.importFromBytes(
          bytes: any(named: 'bytes'),
          fileName: any(named: 'fileName'),
        )).thenAnswer((_) async {});
  });

  setUpAll(() {
    registerFallbackValue(Uint8List(0));
  });

  group('HomeScreen states', () {
    testWidgets('shows loading indicator for ScriptImportLoading',
        (tester) async {
      when(() => cubit.state).thenReturn(const ScriptImportLoading());

      await tester.pumpWidget(_wrap(cubit));
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows error view for ScriptImportError', (tester) async {
      when(() => cubit.state)
          .thenReturn(const ScriptImportError(message: 'Disk full'));

      await tester.pumpWidget(_wrap(cubit));
      await tester.pump();

      expect(find.text('Disk full'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('Retry button calls loadScripts', (tester) async {
      when(() => cubit.state)
          .thenReturn(const ScriptImportError(message: 'Fail'));

      await tester.pumpWidget(_wrap(cubit));
      await tester.pump();

      // Reset call count from initState.
      clearInteractions(cubit);

      await tester.tap(find.text('Retry'));
      await tester.pump();

      verify(() => cubit.loadScripts()).called(1);
    });

    testWidgets('shows script list for loaded state with scripts',
        (tester) async {
      const role = Role(name: 'Hero');
      const script = Script(
        title: 'My Play',
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
      when(() => cubit.state)
          .thenReturn(const ScriptImportLoaded(scripts: [script]));
      when(() => cubit.removeScript(any())).thenReturn(null);

      await tester.pumpWidget(_wrap(cubit));
      await tester.pump();

      expect(find.text('My Play'), findsOneWidget);
      expect(find.text('Horatio'), findsOneWidget); // App bar.
    });

    testWidgets('delete button on script card calls removeScript',
        (tester) async {
      const role = Role(name: 'Hero');
      const script = Script(
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
      when(() => cubit.state)
          .thenReturn(const ScriptImportLoaded(scripts: [script]));
      when(() => cubit.removeScript(any())).thenReturn(null);

      await tester.pumpWidget(_wrap(cubit));
      await tester.pump();

      await tester.tap(find.byIcon(Icons.delete_outline));
      await tester.pump();

      verify(() => cubit.removeScript(0)).called(1);
    });

    testWidgets('tapping import zone calls importFromFile', (tester) async {
      when(() => cubit.state).thenReturn(const ScriptImportInitial());

      await tester.pumpWidget(_wrap(cubit));
      await tester.pumpAndSettle();

      // Reset call count from initState.
      clearInteractions(cubit);

      // Tap the import zone (the "Drop or click to import file" area).
      await tester.tap(find.text('Drop or click to import file'));
      await tester.pump();

      verify(() => cubit.importFromFile()).called(1);
    });

    testWidgets('tapping public domain script calls importFromAsset',
        (tester) async {
      when(() => cubit.state).thenReturn(const ScriptImportInitial());

      await tester.pumpWidget(_wrap(cubit));
      await tester.pumpAndSettle();

      clearInteractions(cubit);

      // Tap a download icon next to a public domain script entry.
      await tester.tap(find.byIcon(Icons.download).first);
      await tester.pump();

      verify(() => cubit.importFromAsset(any())).called(1);
    });
  });

  group('HomeScreen drag-and-drop', () {
    DropTarget findDropTarget(WidgetTester tester) =>
        tester.widget<DropTarget>(find.byType(DropTarget));

    testWidgets('onDragEntered sets isDragging true in empty library',
        (tester) async {
      when(() => cubit.state).thenReturn(const ScriptImportInitial());

      await tester.pumpWidget(_wrap(cubit));
      await tester.pumpAndSettle();

      // Before drag: should show "Drop or click to import file".
      expect(find.text('Drop or click to import file'), findsOneWidget);

      // Simulate drag enter.
      findDropTarget(tester).onDragEntered?.call(
        DropEventDetails(
          localPosition: Offset.zero,
          globalPosition: Offset.zero,
        ),
      );
      await tester.pump();

      // During drag: should show "Drop to import".
      expect(find.text('Drop to import'), findsOneWidget);
    });

    testWidgets('onDragExited resets isDragging false', (tester) async {
      when(() => cubit.state).thenReturn(const ScriptImportInitial());

      await tester.pumpWidget(_wrap(cubit));
      await tester.pumpAndSettle();

      // Enter then exit drag.
      findDropTarget(tester).onDragEntered?.call(
        DropEventDetails(
          localPosition: Offset.zero,
          globalPosition: Offset.zero,
        ),
      );
      await tester.pump();
      expect(find.text('Drop to import'), findsOneWidget);

      findDropTarget(tester).onDragExited?.call(
        DropEventDetails(
          localPosition: Offset.zero,
          globalPosition: Offset.zero,
        ),
      );
      await tester.pump();
      expect(find.text('Drop or click to import file'), findsOneWidget);
    });

    testWidgets('onDragDone imports a supported file', (tester) async {
      when(() => cubit.state).thenReturn(const ScriptImportInitial());

      await tester.pumpWidget(_wrap(cubit));
      await tester.pumpAndSettle();
      clearInteractions(cubit);

      final dropItem = DropItemFile.fromData(
        Uint8List.fromList('HAMLET: Hello.'.codeUnits),
        path: '/tmp/script.txt',
      );
      await tester.runAsync(() async {
        findDropTarget(tester).onDragDone?.call(
          DropDoneDetails(
            files: [dropItem],
            localPosition: Offset.zero,
            globalPosition: Offset.zero,
          ),
        );
        // Let the async _handleDrop complete.
        await Future<void>.delayed(Duration.zero);
      });
      await tester.pump();

      verify(() => cubit.importFromBytes(
            bytes: any(named: 'bytes'),
            fileName: 'script.txt',
          )).called(1);
    });

    testWidgets('onDragDone shows snackbar for unsupported file type',
        (tester) async {
      when(() => cubit.state).thenReturn(const ScriptImportInitial());

      await tester.pumpWidget(_wrap(cubit));
      await tester.pumpAndSettle();

      final dropItem = DropItemFile.fromData(
        Uint8List.fromList('data'.codeUnits),
        path: '/tmp/image.xyz',
      );
      await tester.runAsync(() async {
        findDropTarget(tester).onDragDone?.call(
          DropDoneDetails(
            files: [dropItem],
            localPosition: Offset.zero,
            globalPosition: Offset.zero,
          ),
        );
        await Future<void>.delayed(Duration.zero);
      });
      await tester.pump();

      expect(find.text('Unsupported file type: .xyz'), findsOneWidget);
    });

    testWidgets('drag overlay appears in loaded-with-scripts state',
        (tester) async {
      const role = Role(name: 'Hero');
      const script = Script(
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
      when(() => cubit.state)
          .thenReturn(const ScriptImportLoaded(scripts: [script]));
      when(() => cubit.removeScript(any())).thenReturn(null);

      await tester.pumpWidget(_wrap(cubit));
      await tester.pump();

      // Simulate drag enter to show overlay.
      findDropTarget(tester).onDragEntered?.call(
        DropEventDetails(
          localPosition: Offset.zero,
          globalPosition: Offset.zero,
        ),
      );
      await tester.pump();

      expect(find.text('Drop script file here'), findsOneWidget);
      expect(find.text('.txt  .docx  .pdf'), findsOneWidget);
    });

    testWidgets('tapping script card navigates to role-selection',
        (tester) async {
      const role = Role(name: 'Hero');
      const script = Script(
        title: 'Navigation Play',
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
      when(() => cubit.state)
          .thenReturn(const ScriptImportLoaded(scripts: [script]));
      when(() => cubit.removeScript(any())).thenReturn(null);

      await tester.pumpWidget(_wrap(cubit));
      await tester.pump();

      // Tap the script card (the title text).
      await tester.tap(find.text('Navigation Play'));
      await tester.pumpAndSettle();

      // The /role-selection route should be pushed (it shows an empty
      // Scaffold in the test router).
      expect(find.text('Navigation Play'), findsNothing);
    });
    testWidgets('shouldRepaint evaluates all conditions', (tester) async {
      when(() => cubit.state).thenReturn(const ScriptImportInitial());

      await tester.pumpWidget(_wrap(cubit));
      await tester.pumpAndSettle();

      // Find the CustomPaint that uses _DashedBorderPainter.
      final customPaints =
          tester.widgetList<CustomPaint>(find.byType(CustomPaint));
      final dashedWidget =
          customPaints.firstWhere((cp) => cp.painter != null);
      final painter = dashedWidget.painter!;

      // Same instance → all comparisons evaluate to false → every branch
      // of the || chain executes, covering lines that would otherwise
      // short-circuit.
      expect(painter.shouldRepaint(painter), isFalse);
    });
  });
}
