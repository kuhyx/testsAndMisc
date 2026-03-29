import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/tables/annotation_snapshots_table.dart';
import 'package:horatio_app/database/tables/line_notes_table.dart';
import 'package:horatio_app/database/tables/text_marks_table.dart';
import 'package:horatio_core/horatio_core.dart';

part 'annotation_dao.g.dart';

/// Data access object for annotation persistence.
///
/// [TextMark] and [LineNote] models do not carry a [scriptId] field —
/// the DAO binds it at the persistence boundary.
@DriftAccessor(
  tables: [TextMarksTable, LineNotesTable, AnnotationSnapshotsTable],
)
class AnnotationDao extends DatabaseAccessor<AppDatabase>
    with _$AnnotationDaoMixin {
  /// Creates an [AnnotationDao].
  AnnotationDao(super.db);

  // -- TextMark CRUD --------------------------------------------------------

  /// Watches all marks for a script.
  Stream<List<TextMark>> watchMarksForScript(String scriptId) =>
      (select(textMarksTable)
            ..where((t) => t.scriptId.equals(scriptId))
            ..orderBy([(t) => OrderingTerm.asc(t.lineIndex)]))
          .watch()
          .map((rows) => rows.map(_rowToMark).toList());

  /// Gets marks for a specific line.
  Future<List<TextMark>> getMarksForLine(
    String scriptId,
    int lineIndex,
  ) async {
    final rows = await (select(textMarksTable)
          ..where(
            (t) =>
                t.scriptId.equals(scriptId) &
                t.lineIndex.equals(lineIndex),
          ))
        .get();
    return rows.map(_rowToMark).toList();
  }

  /// Inserts a text mark.
  Future<void> insertMark(String scriptId, TextMark mark) => into(
        textMarksTable,
      ).insert(
        TextMarksTableCompanion.insert(
          id: mark.id,
          scriptId: scriptId,
          lineIndex: mark.lineIndex,
          startOffset: mark.startOffset,
          endOffset: mark.endOffset,
          markType: mark.type.name,
          createdAt: mark.createdAt,
        ),
      );

  /// Deletes a text mark by ID.
  Future<void> deleteMark(String id) =>
      (delete(textMarksTable)..where((t) => t.id.equals(id))).go();

  TextMark _rowToMark(TextMarksTableData row) => TextMark(
        id: row.id,
        lineIndex: row.lineIndex,
        startOffset: row.startOffset,
        endOffset: row.endOffset,
        type: MarkType.values.byName(row.markType),
        createdAt: row.createdAt,
      );

  // -- LineNote CRUD --------------------------------------------------------

  /// Watches all notes for a script.
  Stream<List<LineNote>> watchNotesForScript(String scriptId) =>
      (select(lineNotesTable)
            ..where((t) => t.scriptId.equals(scriptId))
            ..orderBy([(t) => OrderingTerm.asc(t.lineIndex)]))
          .watch()
          .map((rows) => rows.map(_rowToNote).toList());

  /// Gets notes for a specific line.
  Future<List<LineNote>> getNotesForLine(
    String scriptId,
    int lineIndex,
  ) async {
    final rows = await (select(lineNotesTable)
          ..where(
            (t) =>
                t.scriptId.equals(scriptId) &
                t.lineIndex.equals(lineIndex),
          ))
        .get();
    return rows.map(_rowToNote).toList();
  }

  /// Inserts a line note.
  Future<void> insertNote(String scriptId, LineNote note) => into(
        lineNotesTable,
      ).insert(
        LineNotesTableCompanion.insert(
          id: note.id,
          scriptId: scriptId,
          lineIndex: note.lineIndex,
          category: note.category.name,
          noteText: note.text,
          createdAt: note.createdAt,
        ),
      );

  /// Updates the text of a note.
  Future<void> updateNoteText(String id, String text) =>
      (update(lineNotesTable)..where((t) => t.id.equals(id)))
          .write(LineNotesTableCompanion(noteText: Value(text)));

  /// Deletes a note by ID.
  Future<void> deleteNote(String id) =>
      (delete(lineNotesTable)..where((t) => t.id.equals(id))).go();

  LineNote _rowToNote(LineNotesTableData row) => LineNote(
        id: row.id,
        lineIndex: row.lineIndex,
        category: NoteCategory.values.byName(row.category),
        text: row.noteText,
        createdAt: row.createdAt,
      );

  // -- Snapshot management --------------------------------------------------

  /// Watches all snapshots for a script, newest first.
  Stream<List<AnnotationSnapshot>> watchSnapshotsForScript(
    String scriptId,
  ) =>
      (select(annotationSnapshotsTable)
            ..where((t) => t.scriptId.equals(scriptId))
            ..orderBy([(t) => OrderingTerm.desc(t.timestamp)]))
          .watch()
          .map((rows) => rows.map(_rowToSnapshot).toList());

  /// Inserts a snapshot.
  Future<void> insertSnapshot(AnnotationSnapshot snapshot) => into(
        annotationSnapshotsTable,
      ).insert(
        AnnotationSnapshotsTableCompanion.insert(
          id: snapshot.id,
          scriptId: snapshot.scriptId,
          timestamp: snapshot.timestamp,
          snapshotJson: json.encode(snapshot.toJson()),
        ),
      );

  AnnotationSnapshot _rowToSnapshot(AnnotationSnapshotsTableData row) =>
      AnnotationSnapshot.fromJson(
        json.decode(row.snapshotJson) as Map<String, dynamic>,
      );
      // Note: scriptId and timestamp exist in both the table columns (for
      // efficient WHERE/ORDER BY filtering) AND in the JSON blob (for complete
      // deserialization). The columns are the source of truth for queries;
      // the JSON is the source of truth for the full snapshot data.

  // -- Bulk operations (for snapshot restore) -------------------------------

  /// Deletes ALL marks and notes for a script, then inserts the given ones.
  /// Used by snapshot restore.
  Future<void> replaceAllAnnotations({
    required String scriptId,
    required List<TextMark> marks,
    required List<LineNote> notes,
  }) => transaction(() async {
    await (delete(textMarksTable)
          ..where((t) => t.scriptId.equals(scriptId)))
        .go();
    await (delete(lineNotesTable)
          ..where((t) => t.scriptId.equals(scriptId)))
        .go();
    for (final mark in marks) {
      await insertMark(scriptId, mark);
    }
    for (final note in notes) {
      await insertNote(scriptId, note);
    }
  });
}
