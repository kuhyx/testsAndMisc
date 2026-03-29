import 'package:drift/drift.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/database/tables/annotation_snapshots_table.dart';
import 'package:horatio_app/database/tables/line_notes_table.dart';
import 'package:horatio_app/database/tables/text_marks_table.dart';

part 'app_database.g.dart';

/// Central drift database for Horatio.
///
/// Schema version 1: annotation tables (text_marks, line_notes,
/// annotation_snapshots).
@DriftDatabase(
  tables: [TextMarksTable, LineNotesTable, AnnotationSnapshotsTable],
  daos: [AnnotationDao],
)
class AppDatabase extends _$AppDatabase {
  /// Creates an [AppDatabase] with the given [QueryExecutor].
  AppDatabase(super.e);

  @override
  int get schemaVersion => 1;
}
