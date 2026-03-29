import 'package:drift/drift.dart';

/// Drift table for per-line voice recordings.
class LineRecordingsTable extends Table {
  @override
  String get tableName => 'line_recordings';

  TextColumn get id => text()();
  TextColumn get scriptId => text()();
  IntColumn get lineIndex => integer()();
  TextColumn get filePath => text()();
  IntColumn get durationMs => integer()();
  DateTimeColumn get createdAt => dateTime()();
  IntColumn get grade => integer().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}
