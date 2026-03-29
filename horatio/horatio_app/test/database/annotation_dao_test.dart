import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  late AppDatabase db;
  late AnnotationDao dao;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    dao = db.annotationDao;
  });

  tearDown(() => db.close());

  const scriptId = 'script-uuid-1';

  TextMark makeMark({
    String id = 'm1',
    int lineIndex = 0,
    int startOffset = 0,
    int endOffset = 5,
    MarkType type = MarkType.stress,
  }) => TextMark(
    id: id,
    lineIndex: lineIndex,
    startOffset: startOffset,
    endOffset: endOffset,
    type: type,
    createdAt: DateTime.utc(2026, 3, 29),
  );

  LineNote makeNote({
    String id = 'n1',
    int lineIndex = 0,
    NoteCategory category = NoteCategory.intention,
    String text = 'test note',
  }) => LineNote(
    id: id,
    lineIndex: lineIndex,
    category: category,
    text: text,
    createdAt: DateTime.utc(2026, 3, 29),
  );

  group('TextMark CRUD', () {
    test('insertMark and getMarksForLine', () async {
      await dao.insertMark(scriptId, makeMark());
      final marks = await dao.getMarksForLine(scriptId, 0);
      expect(marks.length, 1);
      expect(marks.first.id, 'm1');
      expect(marks.first.type, MarkType.stress);
    });

    test('deleteMark removes mark', () async {
      await dao.insertMark(scriptId, makeMark());
      await dao.deleteMark('m1');
      final marks = await dao.getMarksForLine(scriptId, 0);
      expect(marks, isEmpty);
    });

    test('watchMarksForScript emits on insert', () async {
      final stream = dao.watchMarksForScript(scriptId);
      final future = expectLater(stream, emitsInOrder([isEmpty, hasLength(1)]));
      await Future<void>.delayed(Duration.zero);
      await dao.insertMark(scriptId, makeMark());
      await future;
    });

    test('getMarksForLine filters by scriptId', () async {
      await dao.insertMark(scriptId, makeMark());
      await dao.insertMark('other-script', makeMark(id: 'm2'));
      final marks = await dao.getMarksForLine(scriptId, 0);
      expect(marks.length, 1);
      expect(marks.first.id, 'm1');
    });
  });

  group('LineNote CRUD', () {
    test('insertNote and getNotesForLine', () async {
      await dao.insertNote(scriptId, makeNote());
      final notes = await dao.getNotesForLine(scriptId, 0);
      expect(notes.length, 1);
      expect(notes.first.text, 'test note');
    });

    test('updateNoteText modifies text', () async {
      await dao.insertNote(scriptId, makeNote());
      await dao.updateNoteText('n1', 'updated text');
      final notes = await dao.getNotesForLine(scriptId, 0);
      expect(notes.first.text, 'updated text');
    });

    test('updateNoteCategory modifies category', () async {
      await dao.insertNote(scriptId, makeNote());
      await dao.updateNoteCategory('n1', NoteCategory.emotion);
      final notes = await dao.getNotesForLine(scriptId, 0);
      expect(notes.first.category, NoteCategory.emotion);
    });

    test('deleteNote removes note', () async {
      await dao.insertNote(scriptId, makeNote());
      await dao.deleteNote('n1');
      final notes = await dao.getNotesForLine(scriptId, 0);
      expect(notes, isEmpty);
    });

    test('watchNotesForScript emits on insert', () async {
      final stream = dao.watchNotesForScript(scriptId);
      final future = expectLater(stream, emitsInOrder([isEmpty, hasLength(1)]));
      await Future<void>.delayed(Duration.zero);
      await dao.insertNote(scriptId, makeNote());
      await future;
    });
  });

  group('Snapshot management', () {
    test('insertSnapshot and watch', () async {
      final snapshot = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: scriptId,
        timestamp: DateTime.utc(2026, 3, 29),
        marks: [makeMark()],
        notes: [makeNote()],
      );
      final stream = dao.watchSnapshotsForScript(scriptId);
      final future = expectLater(stream, emitsInOrder([isEmpty, hasLength(1)]));
      await Future<void>.delayed(Duration.zero);
      await dao.insertSnapshot(snapshot);
      await future;
    });
  });

  group('replaceAllAnnotations', () {
    test('deletes existing and inserts new', () async {
      await dao.insertMark(scriptId, makeMark(id: 'old-m'));
      await dao.insertNote(scriptId, makeNote(id: 'old-n'));

      await dao.replaceAllAnnotations(
        scriptId: scriptId,
        marks: [makeMark(id: 'new-m')],
        notes: [makeNote(id: 'new-n', text: 'new note')],
      );

      final marks = await dao.getMarksForLine(scriptId, 0);
      expect(marks.length, 1);
      expect(marks.first.id, 'new-m');

      final notes = await dao.getNotesForLine(scriptId, 0);
      expect(notes.length, 1);
      expect(notes.first.id, 'new-n');
    });

    test('does not affect other scripts', () async {
      await dao.insertMark('other-script', makeMark(id: 'keep-m'));
      await dao.replaceAllAnnotations(scriptId: scriptId, marks: [], notes: []);
      final marks = await dao.getMarksForLine('other-script', 0);
      expect(marks.length, 1);
      expect(marks.first.id, 'keep-m');
    });
  });
}
