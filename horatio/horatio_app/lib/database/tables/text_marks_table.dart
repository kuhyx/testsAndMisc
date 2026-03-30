// coverage:ignore-file
import 'package:drift/drift.dart';

/// Drift table for text-level delivery marks on script lines.
class TextMarksTable extends Table {
  @override
  String get tableName => 'text_marks';

  TextColumn get id => text()();
  TextColumn get scriptId => text()();
  IntColumn get lineIndex => integer()();
  IntColumn get startOffset => integer()();
  IntColumn get endOffset => integer()();
  TextColumn get markType => text()();
  DateTimeColumn get createdAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}
