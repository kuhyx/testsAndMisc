// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file

part of 'annotation_dao.dart';

// ignore_for_file: type=lint
mixin _$AnnotationDaoMixin on DatabaseAccessor<AppDatabase> {
  $TextMarksTableTable get textMarksTable => attachedDatabase.textMarksTable;
  $LineNotesTableTable get lineNotesTable => attachedDatabase.lineNotesTable;
  $AnnotationSnapshotsTableTable get annotationSnapshotsTable =>
      attachedDatabase.annotationSnapshotsTable;
  AnnotationDaoManager get managers => AnnotationDaoManager(this);
}

class AnnotationDaoManager {
  final _$AnnotationDaoMixin _db;
  AnnotationDaoManager(this._db);
  $$TextMarksTableTableTableManager get textMarksTable =>
      $$TextMarksTableTableTableManager(
        _db.attachedDatabase,
        _db.textMarksTable,
      );
  $$LineNotesTableTableTableManager get lineNotesTable =>
      $$LineNotesTableTableTableManager(
        _db.attachedDatabase,
        _db.lineNotesTable,
      );
  $$AnnotationSnapshotsTableTableTableManager get annotationSnapshotsTable =>
      $$AnnotationSnapshotsTableTableTableManager(
        _db.attachedDatabase,
        _db.annotationSnapshotsTable,
      );
}
