// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file

part of 'recording_dao.dart';

// ignore_for_file: type=lint
mixin _$RecordingDaoMixin on DatabaseAccessor<AppDatabase> {
  $LineRecordingsTableTable get lineRecordingsTable =>
      attachedDatabase.lineRecordingsTable;
  RecordingDaoManager get managers => RecordingDaoManager(this);
}

class RecordingDaoManager {
  final _$RecordingDaoMixin _db;
  RecordingDaoManager(this._db);
  $$LineRecordingsTableTableTableManager get lineRecordingsTable =>
      $$LineRecordingsTableTableTableManager(
        _db.attachedDatabase,
        _db.lineRecordingsTable,
      );
}
