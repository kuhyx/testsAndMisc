import 'package:drift/drift.dart';

/// Drift table for annotation history snapshots.
class AnnotationSnapshotsTable extends Table {
  @override
  String get tableName => 'annotation_snapshots';

  TextColumn get id => text()();
  TextColumn get scriptId => text()();
  DateTimeColumn get timestamp => dateTime()();
  TextColumn get snapshotJson => text()();

  @override
  Set<Column> get primaryKey => {id};
}
