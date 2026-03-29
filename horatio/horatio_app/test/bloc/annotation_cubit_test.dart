import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/annotation/annotation_cubit.dart';
import 'package:horatio_app/bloc/annotation/annotation_state.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:mocktail/mocktail.dart';

class MockAnnotationDao extends Mock implements AnnotationDao {}

void main() {
  late MockAnnotationDao dao;
  late StreamController<List<TextMark>> marksController;
  late StreamController<List<LineNote>> notesController;

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

  setUp(() {
    dao = MockAnnotationDao();
    marksController = StreamController<List<TextMark>>.broadcast();
    notesController = StreamController<List<LineNote>>.broadcast();

    when(
      () => dao.watchMarksForScript(scriptId),
    ).thenAnswer((_) => marksController.stream);
    when(
      () => dao.watchNotesForScript(scriptId),
    ).thenAnswer((_) => notesController.stream);
  });

  tearDown(() {
    marksController.close();
    notesController.close();
  });

  setUpAll(() {
    registerFallbackValue(testMark);
    registerFallbackValue(testNote);
    registerFallbackValue(NoteCategory.intention);
  });

  group('AnnotationCubit', () {
    test('initial state is AnnotationInitial', () {
      final cubit = AnnotationCubit(dao: dao);
      expect(cubit.state, isA<AnnotationInitial>());
      cubit.close();
    });

    test('loadAnnotations subscribes and emits on marks stream', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([testMark]);
      await Future<void>.delayed(Duration.zero);
      final state = cubit.state;
      expect(state, isA<AnnotationLoaded>());
      expect((state as AnnotationLoaded).marks, [testMark]);
      await cubit.close();
    });

    test('loadAnnotations subscribes and emits on notes stream', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      notesController.add([testNote]);
      await Future<void>.delayed(Duration.zero);
      final state = cubit.state;
      expect(state, isA<AnnotationLoaded>());
      expect((state as AnnotationLoaded).notes, [testNote]);
      await cubit.close();
    });

    test('loadAnnotations double-emits on both streams', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([testMark]);
      notesController.add([testNote]);
      await Future<void>.delayed(Duration.zero);
      final state = cubit.state as AnnotationLoaded;
      expect(state.marks, [testMark]);
      expect(state.notes, [testNote]);
      await cubit.close();
    });

    test('selectLine updates selectedLineIndex', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([]);
      await Future<void>.delayed(Duration.zero);
      cubit.selectLine(3);
      expect((cubit.state as AnnotationLoaded).selectedLineIndex, 3);
      await cubit.close();
    });

    test('selectLine is no-op when state is AnnotationInitial', () {
      final cubit = AnnotationCubit(dao: dao)
        ..selectLine(3); // Should not throw
      expect(cubit.state, isA<AnnotationInitial>());
      cubit.close();
    });

    test('startEditing / cancelEditing toggle EditingContext', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([]);
      await Future<void>.delayed(Duration.zero);

      cubit.startEditing(lineIndex: 2, isAddingMark: true);
      final editing = (cubit.state as AnnotationLoaded).editing;
      expect(editing, isNotNull);
      expect(editing!.lineIndex, 2);
      expect(editing.isAddingMark, isTrue);

      cubit.cancelEditing();
      expect((cubit.state as AnnotationLoaded).editing, isNull);
      await cubit.close();
    });

    test('EditingContext equality', () {
      const a = EditingContext(lineIndex: 1, isAddingMark: true);
      const b = EditingContext(lineIndex: 1, isAddingMark: true);
      const c = EditingContext(lineIndex: 2, isAddingMark: false);
      expect(a, equals(b));
      expect(a, isNot(equals(c)));
    });

    test('startEditing is no-op when state is AnnotationInitial', () {
      final cubit = AnnotationCubit(dao: dao)
        ..startEditing(lineIndex: 0, isAddingMark: true);
      expect(cubit.state, isA<AnnotationInitial>());
      cubit.close();
    });

    test('cancelEditing is no-op when state is AnnotationInitial', () {
      final cubit = AnnotationCubit(dao: dao)..cancelEditing();
      expect(cubit.state, isA<AnnotationInitial>());
      cubit.close();
    });

    test('selectedLineIndex preserved across stream updates', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([]);
      await Future<void>.delayed(Duration.zero);
      cubit.selectLine(5);
      marksController.add([testMark]); // stream update
      await Future<void>.delayed(Duration.zero);
      expect((cubit.state as AnnotationLoaded).selectedLineIndex, 5);
      await cubit.close();
    });

    test('addMark calls dao.insertMark', () async {
      when(() => dao.insertMark(any(), any())).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.addMark(
        lineIndex: 0,
        startOffset: 0,
        endOffset: 5,
        type: MarkType.stress,
      );
      verify(() => dao.insertMark(scriptId, any())).called(1);
      await cubit.close();
    });

    test('addMark is no-op when scriptId is null', () async {
      final cubit = AnnotationCubit(dao: dao);
      await cubit.addMark(
        lineIndex: 0,
        startOffset: 0,
        endOffset: 5,
        type: MarkType.stress,
      );
      verifyNever(() => dao.insertMark(any(), any()));
      await cubit.close();
    });

    test('removeMark calls dao.deleteMark', () async {
      when(() => dao.deleteMark('m1')).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao);
      await cubit.removeMark('m1');
      verify(() => dao.deleteMark('m1')).called(1);
      await cubit.close();
    });

    test('addNote calls dao.insertNote', () async {
      when(() => dao.insertNote(any(), any())).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      marksController.add([]);
      await Future<void>.delayed(Duration.zero);

      await cubit.addNote(
        lineIndex: 0,
        category: NoteCategory.intention,
        text: 'test note',
      );
      verify(() => dao.insertNote(scriptId, any())).called(1);
      await cubit.close();
    });

    test('addNote is no-op when scriptId is null', () async {
      final cubit = AnnotationCubit(dao: dao);
      await cubit.addNote(
        lineIndex: 0,
        category: NoteCategory.intention,
        text: 'test',
      );
      verifyNever(() => dao.insertNote(any(), any()));
      await cubit.close();
    });

    test('updateNote calls dao.updateNoteText', () async {
      when(() => dao.updateNoteText('n1', 'new')).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao);
      await cubit.updateNote('n1', text: 'new');
      verify(() => dao.updateNoteText('n1', 'new')).called(1);
      await cubit.close();
    });

    test('updateNote calls dao.updateNoteCategory', () async {
      when(
        () => dao.updateNoteCategory('n1', NoteCategory.emotion),
      ).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao);
      await cubit.updateNote('n1', category: NoteCategory.emotion);
      verify(
        () => dao.updateNoteCategory('n1', NoteCategory.emotion),
      ).called(1);
      await cubit.close();
    });

    test('updateNote with both text and category', () async {
      when(() => dao.updateNoteText('n1', 'new')).thenAnswer((_) async {});
      when(
        () => dao.updateNoteCategory('n1', NoteCategory.blocking),
      ).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao);
      await cubit.updateNote(
        'n1',
        text: 'new',
        category: NoteCategory.blocking,
      );
      verify(() => dao.updateNoteText('n1', 'new')).called(1);
      verify(
        () => dao.updateNoteCategory('n1', NoteCategory.blocking),
      ).called(1);
      await cubit.close();
    });

    test('updateNote with no arguments is no-op', () async {
      final cubit = AnnotationCubit(dao: dao);
      await cubit.updateNote('n1');
      verifyNever(() => dao.updateNoteText(any(), any()));
      verifyNever(() => dao.updateNoteCategory(any(), any()));
      await cubit.close();
    });

    test('removeNote calls dao.deleteNote', () async {
      when(() => dao.deleteNote('n1')).thenAnswer((_) async {});
      final cubit = AnnotationCubit(dao: dao);
      await cubit.removeNote('n1');
      verify(() => dao.deleteNote('n1')).called(1);
      await cubit.close();
    });

    test(
      'loadAnnotations with new scriptId cancels previous streams',
      () async {
        final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
        marksController.add([testMark]);
        await Future<void>.delayed(Duration.zero);

        final marks2 = StreamController<List<TextMark>>.broadcast();
        final notes2 = StreamController<List<LineNote>>.broadcast();
        when(
          () => dao.watchMarksForScript('script-2'),
        ).thenAnswer((_) => marks2.stream);
        when(
          () => dao.watchNotesForScript('script-2'),
        ).thenAnswer((_) => notes2.stream);

        cubit.loadAnnotations('script-2');
        marks2.add([]);
        notes2.add([]);
        await Future<void>.delayed(Duration.zero);

        final state = cubit.state;
        expect(state, isA<AnnotationLoaded>());
        expect((state as AnnotationLoaded).scriptId, 'script-2');
        expect(state.marks, isEmpty);

        await cubit.close();
        await marks2.close();
        await notes2.close();
      },
    );

    test('close cancels stream subscriptions', () async {
      final cubit = AnnotationCubit(dao: dao)..loadAnnotations(scriptId);
      await cubit.close();
      // Adding to controller after close should not cause errors.
      marksController.add([]);
      notesController.add([]);
    });
  });
}
