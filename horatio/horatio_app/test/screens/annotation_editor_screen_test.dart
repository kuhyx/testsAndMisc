import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/screens/annotation_editor_screen.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockAnnotationDao extends Mock implements AnnotationDao {}

const _hamlet = Role(name: 'Hamlet');
const _horatio = Role(name: 'Horatio');

Script _testScript() => const Script(
      id: 'editor-screen-test',
      title: 'Test Play',
      roles: [_hamlet, _horatio],
      scenes: [
        Scene(
          lines: [
            ScriptLine(
              text: 'To be or not to be.',
              role: _hamlet,
              sceneIndex: 0,
              lineIndex: 0,
            ),
            ScriptLine(
              text: 'Indeed, my lord.',
              role: _horatio,
              sceneIndex: 0,
              lineIndex: 1,
            ),
          ],
        ),
      ],
    );

late MockAnnotationDao _dao;
late StreamController<List<TextMark>> _marksCtrl;
late StreamController<List<LineNote>> _notesCtrl;
late StreamController<List<AnnotationSnapshot>> _snapshotsCtrl;

void _setUpDao() {
  _dao = MockAnnotationDao();
  _marksCtrl = StreamController<List<TextMark>>.broadcast();
  _notesCtrl = StreamController<List<LineNote>>.broadcast();
  _snapshotsCtrl = StreamController<List<AnnotationSnapshot>>.broadcast();

  when(() => _dao.watchMarksForScript(any()))
      .thenAnswer((_) => _marksCtrl.stream);
  when(() => _dao.watchNotesForScript(any()))
      .thenAnswer((_) => _notesCtrl.stream);
  when(() => _dao.watchSnapshotsForScript(any()))
      .thenAnswer((_) => _snapshotsCtrl.stream);
  when(() => _dao.insertSnapshot(any())).thenAnswer((_) async {});
  when(() => _dao.insertMark(any(), any())).thenAnswer((_) async {});
  when(() => _dao.insertNote(any(), any())).thenAnswer((_) async {});
}

void _tearDownStreams() {
  _marksCtrl.close();
  _notesCtrl.close();
  _snapshotsCtrl.close();
}

Widget _buildScreen(Script script) => RepositoryProvider<AnnotationDao>.value(
      value: _dao,
      child: MaterialApp(
        home: AnnotationEditorScreen(script: script),
      ),
    );

Widget _buildScreenWithRouter(Script script) {
  final router = GoRouter(
    initialLocation: '/annotations',
    routes: [
      GoRoute(
        path: '/annotations',
        builder: (context, state) => RepositoryProvider<AnnotationDao>.value(
          value: _dao,
          child: AnnotationEditorScreen(script: script),
        ),
      ),
      GoRoute(
        path: '/annotation-history',
        builder: (context, state) =>
            const Scaffold(body: Text('History Screen')),
      ),
    ],
  );
  return MaterialApp.router(routerConfig: router);
}

void main() {
  setUpAll(() {
    registerFallbackValue(
      AnnotationSnapshot(
        id: 'fb',
        scriptId: 'fb',
        timestamp: DateTime.utc(2026),
        marks: const [],
        notes: const [],
      ),
    );
    registerFallbackValue(
      TextMark(
        id: 'fb',
        lineIndex: 0,
        startOffset: 0,
        endOffset: 1,
        type: MarkType.stress,
        createdAt: DateTime.utc(2026),
      ),
    );
    registerFallbackValue(
      LineNote(
        id: 'fb',
        lineIndex: 0,
        category: NoteCategory.general,
        text: 'fb',
        createdAt: DateTime.utc(2026),
      ),
    );
  });

  group('AnnotationEditorScreen', () {
    setUp(_setUpDao);
    tearDown(_tearDownStreams);

    testWidgets('shows loading indicator in initial state', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      // Streams haven't emitted yet → AnnotationInitial.
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows script lines after data loads', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      expect(
        find.text('To be or not to be.', findRichText: true),
        findsOneWidget,
      );
      expect(
        find.text('Indeed, my lord.', findRichText: true),
        findsOneWidget,
      );
    });

    testWidgets('lines with marks show colored overlay', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([
        TextMark(
          id: 'm1',
          lineIndex: 0,
          startOffset: 0,
          endOffset: 5,
          type: MarkType.stress,
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      // MarkOverlay renders RichText widgets.
      expect(find.byType(RichText), findsWidgets);
      expect(find.text('To be or not to be.'), findsNothing);
    });

    testWidgets('lines with notes show note indicator badge',
        (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'test note',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      expect(find.text('1'), findsOneWidget);
    });

    testWidgets('tapping a line highlights it', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(
        find.text('To be or not to be.', findRichText: true),
      );
      await tester.pump();

      // After tap, a Container with primary color should appear.
      final containers = tester
          .widgetList<Container>(find.byType(Container))
          .where((c) => c.color != null);
      expect(containers, isNotEmpty);
    });

    testWidgets('History button is present and navigates', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreenWithRouter(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.history), findsOneWidget);
      await tester.tap(find.byIcon(Icons.history));
      await tester.pumpAndSettle();

      expect(find.text('History Screen'), findsOneWidget);
    });

    testWidgets('long-press on a line shows mark type picker',
        (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.longPress(
        find.text('To be or not to be.', findRichText: true),
      );
      await tester.pumpAndSettle();

      expect(find.text('Add Mark'), findsOneWidget);
      expect(find.text('Stress'), findsOneWidget);
      expect(find.text('Pause'), findsOneWidget);
    });

    testWidgets('selecting mark type in picker calls addMark',
        (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.longPress(
        find.text('To be or not to be.', findRichText: true),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Stress'));
      await tester.pumpAndSettle();

      verify(() => _dao.insertMark(any(), any())).called(1);
    });

    testWidgets('cancel in mark picker dismisses dialog', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.longPress(
        find.text('To be or not to be.', findRichText: true),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      expect(find.text('Add Mark'), findsNothing);
    });

    testWidgets('tapping note indicator shows note editor sheet',
        (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'existing note',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('1'));
      await tester.pumpAndSettle();

      expect(find.text('Category'), findsOneWidget);
      expect(find.text('Save'), findsOneWidget);
    });

    testWidgets('saving note in editor calls addNote', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'existing note',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('1'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextFormField), 'New note text');
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      verify(() => _dao.insertNote(any(), any())).called(1);
    });

    testWidgets('cancel in note editor sheet dismisses', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([
        LineNote(
          id: 'n1',
          lineIndex: 0,
          category: NoteCategory.intention,
          text: 'existing note',
          createdAt: DateTime.utc(2026),
        ),
      ]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('1'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      expect(find.text('Category'), findsNothing);
    });

    testWidgets('FAB saves snapshot', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _marksCtrl.add([]);
      _notesCtrl.add([]);
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      verify(() => _dao.insertSnapshot(any())).called(1);
    });

    testWidgets('FAB hidden in initial state', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      // Streams haven't emitted → initial state.
      expect(find.byType(FloatingActionButton), findsNothing);
    });

    testWidgets('AppBar shows script title', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      expect(find.text('Annotate: Test Play'), findsOneWidget);
    });
  });
}
