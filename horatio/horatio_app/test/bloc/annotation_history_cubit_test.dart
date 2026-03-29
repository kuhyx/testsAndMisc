import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/annotation/annotation_history_cubit.dart';
import 'package:horatio_app/bloc/annotation/annotation_history_state.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockAnnotationDao extends Mock implements AnnotationDao {}

void main() {
  late MockAnnotationDao dao;
  late StreamController<List<AnnotationSnapshot>> snapshotsController;

  const scriptId = 'script-1';

  final testMark = TextMark(
    id: 'm1',
    lineIndex: 0,
    startOffset: 0,
    endOffset: 5,
    type: MarkType.stress,
    createdAt: DateTime.utc(2026),
  );

  final testNote = LineNote(
    id: 'n1',
    lineIndex: 0,
    category: NoteCategory.intention,
    text: 'test',
    createdAt: DateTime.utc(2026),
  );

  final testSnapshot = AnnotationSnapshot(
    id: 'snap-1',
    scriptId: scriptId,
    timestamp: DateTime.utc(2026, 3, 29),
    marks: [testMark],
    notes: [testNote],
  );

  setUp(() {
    dao = MockAnnotationDao();
    snapshotsController =
        StreamController<List<AnnotationSnapshot>>.broadcast();
    when(() => dao.watchSnapshotsForScript(scriptId))
        .thenAnswer((_) => snapshotsController.stream);
  });

  tearDown(() => snapshotsController.close());

  setUpAll(() {
    registerFallbackValue(testSnapshot);
  });

  group('AnnotationHistoryCubit', () {
    test('initial state is AnnotationHistoryInitial', () {
      final cubit = AnnotationHistoryCubit(dao: dao);
      expect(cubit.state, isA<AnnotationHistoryInitial>());
      expect(cubit.state, equals(const AnnotationHistoryInitial()));
      expect(const AnnotationHistoryInitial().props, isEmpty);
      cubit.close();
    });

    test('loadSnapshots subscribes and emits AnnotationHistoryLoaded',
        () async {
      final cubit = AnnotationHistoryCubit(dao: dao)
        ..loadSnapshots(scriptId);
      snapshotsController.add([testSnapshot]);
      await Future<void>.delayed(Duration.zero);
      final state = cubit.state;
      expect(state, isA<AnnotationHistoryLoaded>());
      expect((state as AnnotationHistoryLoaded).snapshots, [testSnapshot]);
      await cubit.close();
    });

    test('saveSnapshot calls dao.insertSnapshot with correct data', () async {
      when(() => dao.insertSnapshot(any())).thenAnswer((_) async {});
      final cubit = AnnotationHistoryCubit(dao: dao)
        ..loadSnapshots(scriptId);
      snapshotsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.saveSnapshot(marks: [testMark], notes: [testNote]);
      final captured =
          verify(() => dao.insertSnapshot(captureAny())).captured.single
              as AnnotationSnapshot;
      expect(captured.scriptId, scriptId);
      expect(captured.marks, [testMark]);
      expect(captured.notes, [testNote]);
      await cubit.close();
    });

    test('saveSnapshot is no-op when scriptId is null', () async {
      final cubit = AnnotationHistoryCubit(dao: dao);
      await cubit.saveSnapshot(marks: [], notes: []);
      verifyNever(() => dao.insertSnapshot(any()));
      await cubit.close();
    });

    test('restoreSnapshot calls dao.replaceAllAnnotations', () async {
      when(
        () => dao.replaceAllAnnotations(
          scriptId: any(named: 'scriptId'),
          marks: any(named: 'marks'),
          notes: any(named: 'notes'),
        ),
      ).thenAnswer((_) async {});
      final cubit = AnnotationHistoryCubit(dao: dao)
        ..loadSnapshots(scriptId);
      snapshotsController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.restoreSnapshot(testSnapshot);
      verify(
        () => dao.replaceAllAnnotations(
          scriptId: scriptId,
          marks: testSnapshot.marks,
          notes: testSnapshot.notes,
        ),
      ).called(1);
      await cubit.close();
    });

    test('restoreSnapshot is no-op when scriptId is null', () async {
      final cubit = AnnotationHistoryCubit(dao: dao);
      await cubit.restoreSnapshot(testSnapshot);
      verifyNever(
        () => dao.replaceAllAnnotations(
          scriptId: any(named: 'scriptId'),
          marks: any(named: 'marks'),
          notes: any(named: 'notes'),
        ),
      );
      await cubit.close();
    });

    test('loadSnapshots with new scriptId cancels previous stream', () async {
      final cubit = AnnotationHistoryCubit(dao: dao)
        ..loadSnapshots(scriptId);
      snapshotsController.add([testSnapshot]);
      await Future<void>.delayed(Duration.zero);

      final snapshots2 = StreamController<List<AnnotationSnapshot>>.broadcast();
      when(() => dao.watchSnapshotsForScript('script-2'))
          .thenAnswer((_) => snapshots2.stream);

      cubit.loadSnapshots('script-2');
      snapshots2.add([]);
      await Future<void>.delayed(Duration.zero);

      final state = cubit.state;
      expect(state, isA<AnnotationHistoryLoaded>());
      expect((state as AnnotationHistoryLoaded).snapshots, isEmpty);

      await cubit.close();
      await snapshots2.close();
    });

    test('close cancels stream subscription', () async {
      final cubit = AnnotationHistoryCubit(dao: dao)
        ..loadSnapshots(scriptId);
      await cubit.close();
      snapshotsController.add([testSnapshot]);
      // Should not cause errors.
    });
  });
}
