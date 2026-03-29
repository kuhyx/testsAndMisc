import 'package:drift/drift.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_app/database/tables/annotation_snapshots_table.dart';
import 'package:horatio_app/database/tables/line_notes_table.dart';
import 'package:horatio_app/database/tables/line_recordings_table.dart';
import 'package:horatio_app/database/tables/text_marks_table.dart';

part 'app_database.g.dart';

/// Central drift database for Horatio.
///
/// Schema version 2: adds line_recordings table for voice recordings.
@DriftDatabase(
  tables: [
    TextMarksTable,
    LineNotesTable,
    AnnotationSnapshotsTable,
    LineRecordingsTable,
  ],
  daos: [AnnotationDao, RecordingDao],
)
class AppDatabase extends _$AppDatabase {
  /// Creates an [AppDatabase] with the given [QueryExecutor].
  AppDatabase(super.e);

  @override
  int get schemaVersion => 2;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (m) => m.createAll(),
        onUpgrade: (m, from, to) async {
          if (from < 2) {
            await m.createTable(lineRecordingsTable);
          }
        },
      );
}
