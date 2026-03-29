import 'package:drift/drift.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/tables/line_recordings_table.dart';
import 'package:horatio_core/horatio_core.dart';

part 'recording_dao.g.dart';

/// Data access object for voice recording persistence.
@DriftAccessor(tables: [LineRecordingsTable])
class RecordingDao extends DatabaseAccessor<AppDatabase>
    with _$RecordingDaoMixin {
  /// Creates a [RecordingDao].
  RecordingDao(super.db);

  /// Watches all recordings for a script, ordered by lineIndex.
  Stream<List<LineRecording>> watchRecordingsForScript(String scriptId) =>
      (select(lineRecordingsTable)
            ..where((t) => t.scriptId.equals(scriptId))
            ..orderBy([(t) => OrderingTerm.asc(t.lineIndex)]))
          .watch()
          .map((rows) => rows.map(_rowToRecording).toList());

  /// Inserts a recording.
  Future<void> insertRecording(String scriptId, LineRecording recording) =>
      into(lineRecordingsTable).insert(
        LineRecordingsTableCompanion.insert(
          id: recording.id,
          scriptId: scriptId,
          lineIndex: recording.lineIndex,
          filePath: recording.filePath,
          durationMs: recording.durationMs,
          createdAt: recording.createdAt,
          grade: Value(recording.grade),
        ),
      );

  /// Deletes a recording by ID.
  Future<void> deleteRecording(String id) =>
      (delete(lineRecordingsTable)..where((t) => t.id.equals(id))).go();

  /// Updates or clears the grade of a recording.
  Future<void> updateRecordingGrade(String id, int? grade) =>
      (update(lineRecordingsTable)..where((t) => t.id.equals(id)))
          .write(LineRecordingsTableCompanion(grade: Value(grade)));

  LineRecording _rowToRecording(LineRecordingsTableData row) =>
      LineRecording(
        id: row.id,
        scriptId: row.scriptId,
        lineIndex: row.lineIndex,
        filePath: row.filePath,
        durationMs: row.durationMs,
        createdAt: row.createdAt,
        grade: row.grade,
      );
}
