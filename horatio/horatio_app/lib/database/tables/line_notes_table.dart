import 'package:drift/drift.dart';

/// Drift table for line-level interpretive notes.
class LineNotesTable extends Table {
  @override
  String get tableName => 'line_notes';

  TextColumn get id => text()();
  TextColumn get scriptId => text()();
  IntColumn get lineIndex => integer()();
  TextColumn get category => text()();
  TextColumn get noteText => text()();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}
