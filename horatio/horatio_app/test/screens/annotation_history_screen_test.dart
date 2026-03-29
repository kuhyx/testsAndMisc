import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/screens/annotation_history_screen.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockAnnotationDao extends Mock implements AnnotationDao {}

const _hamlet = Role(name: 'Hamlet');

Script _testScript() => const Script(
      id: 'history-screen-test',
      title: 'Test Play',
      roles: [_hamlet],
      scenes: [
        Scene(
          lines: [
            ScriptLine(
              text: 'To be.',
              role: _hamlet,
              sceneIndex: 0,
              lineIndex: 0,
            ),
          ],
        ),
      ],
    );

late MockAnnotationDao _dao;
late StreamController<List<AnnotationSnapshot>> _snapshotsCtrl;

void _setUpDao() {
  _dao = MockAnnotationDao();
  _snapshotsCtrl = StreamController<List<AnnotationSnapshot>>.broadcast();

  when(() => _dao.watchSnapshotsForScript(any()))
      .thenAnswer((_) => _snapshotsCtrl.stream);
  when(() => _dao.replaceAllAnnotations(
        scriptId: any(named: 'scriptId'),
        marks: any(named: 'marks'),
        notes: any(named: 'notes'),
      )).thenAnswer((_) async {});
}

Widget _buildScreen(Script script) =>
    RepositoryProvider<AnnotationDao>.value(
      value: _dao,
      child: MaterialApp(
        home: AnnotationHistoryScreen(script: script),
      ),
    );

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
  });

  group('AnnotationHistoryScreen', () {
    setUp(_setUpDao);
    tearDown(() => _snapshotsCtrl.close());

    testWidgets('shows loading indicator in initial state', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows "No history yet" when snapshots list is empty',
        (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));
      _snapshotsCtrl.add([]);
      await tester.pumpAndSettle();

      expect(find.text('No history yet'), findsOneWidget);
    });

    testWidgets('renders snapshot cards with timestamp and counts',
        (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      final snapshot = AnnotationSnapshot(
        id: 's1',
        scriptId: 'history-screen-test',
        timestamp: DateTime.utc(2026, 3, 15, 10, 30),
        marks: [
          TextMark(
            id: 'm1',
            lineIndex: 0,
            startOffset: 0,
            endOffset: 2,
            type: MarkType.stress,
            createdAt: DateTime.utc(2026),
          ),
        ],
        notes: [
          LineNote(
            id: 'n1',
            lineIndex: 0,
            category: NoteCategory.general,
            text: 'note',
            createdAt: DateTime.utc(2026),
          ),
          LineNote(
            id: 'n2',
            lineIndex: 0,
            category: NoteCategory.emotion,
            text: 'another',
            createdAt: DateTime.utc(2026),
          ),
        ],
      );
      _snapshotsCtrl.add([snapshot]);
      await tester.pumpAndSettle();

      expect(find.text('1 marks · 2 notes'), findsOneWidget);
      expect(find.text('Restore'), findsOneWidget);
    });

    testWidgets('Restore button shows confirmation dialog', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      final snapshot = AnnotationSnapshot(
        id: 's1',
        scriptId: 'history-screen-test',
        timestamp: DateTime.utc(2026, 3, 15, 10, 30),
        marks: const [],
        notes: const [],
      );
      _snapshotsCtrl.add([snapshot]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Restore'));
      await tester.pumpAndSettle();

      expect(find.text('Restore Snapshot?'), findsOneWidget);
      expect(
        find.text(
          'This will replace all current annotations with the snapshot.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('confirming restore calls cubit method', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      final snapshot = AnnotationSnapshot(
        id: 's1',
        scriptId: 'history-screen-test',
        timestamp: DateTime.utc(2026, 3, 15, 10, 30),
        marks: const [],
        notes: const [],
      );
      _snapshotsCtrl.add([snapshot]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Restore'));
      await tester.pumpAndSettle();

      // Tap 'Restore' in dialog (the second one on screen).
      await tester.tap(find.widgetWithText(TextButton, 'Restore').last);
      await tester.pumpAndSettle();

      verify(
        () => _dao.replaceAllAnnotations(
          scriptId: any(named: 'scriptId'),
          marks: any(named: 'marks'),
          notes: any(named: 'notes'),
        ),
      ).called(1);
    });

    testWidgets('cancelling dialog dismisses without restore',
        (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      final snapshot = AnnotationSnapshot(
        id: 's1',
        scriptId: 'history-screen-test',
        timestamp: DateTime.utc(2026, 3, 15, 10, 30),
        marks: const [],
        notes: const [],
      );
      _snapshotsCtrl.add([snapshot]);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Restore'));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(TextButton, 'Cancel'));
      await tester.pumpAndSettle();

      expect(find.text('Restore Snapshot?'), findsNothing);
      verifyNever(
        () => _dao.replaceAllAnnotations(
          scriptId: any(named: 'scriptId'),
          marks: any(named: 'marks'),
          notes: any(named: 'notes'),
        ),
      );
    });

    testWidgets('AppBar shows script title', (tester) async {
      final script = _testScript();
      await tester.pumpWidget(_buildScreen(script));

      expect(find.text('History: Test Play'), findsOneWidget);
    });
  });
}
