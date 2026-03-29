import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:mocktail/mocktail.dart';

class _MockMigrator extends Mock implements Migrator {}

void main() {
  group('AppDatabase', () {
    test('schema version is 2', () {
      final db = AppDatabase(NativeDatabase.memory());
      addTearDown(db.close);
      expect(db.schemaVersion, 2);
    });

    test('migration from v1 creates lineRecordingsTable', () async {
      final db = AppDatabase(NativeDatabase.memory());
      addTearDown(db.close);
      final migrator = _MockMigrator();
      when(
        () => migrator.createTable(db.lineRecordingsTable),
      ).thenAnswer((_) async {});

      final onUpgrade = db.migration.onUpgrade;
      await onUpgrade(migrator, 1, 2);

      verify(() => migrator.createTable(db.lineRecordingsTable)).called(1);
    });

    test('migration from v2 does not create lineRecordingsTable', () async {
      final db = AppDatabase(NativeDatabase.memory());
      addTearDown(db.close);
      final migrator = _MockMigrator();

      final onUpgrade = db.migration.onUpgrade;
      await onUpgrade(migrator, 2, 2);

      verifyNever(() => migrator.createTable(db.lineRecordingsTable));
    });
  });
}
