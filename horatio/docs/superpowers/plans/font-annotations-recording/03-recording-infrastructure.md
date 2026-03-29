## Chunk 3: Recording Infrastructure (Model + Table + Migration + DAO)

### Task 3.1: LineRecording model in horatio_core

**Files:**

- Create: `horatio_core/lib/src/models/line_recording.dart`
- Modify: `horatio_core/lib/src/models/models.dart`
- Create: `horatio_core/test/models/line_recording_test.dart`

- [ ] **Step 1: Write failing tests**

```dart
import 'package:horatio_core/horatio_core.dart';
import 'package:test/test.dart';

void main() {
  group('LineRecording', () {
    final recording = LineRecording(
      id: 'r1',
      scriptId: 's1',
      lineIndex: 0,
      filePath: '/recordings/s1/line_0_123.m4a',
      durationMs: 5000,
      createdAt: DateTime.utc(2026),
      grade: 3,
    );

    test('properties are accessible', () {
      expect(recording.id, 'r1');
      expect(recording.scriptId, 's1');
      expect(recording.lineIndex, 0);
      expect(recording.filePath, '/recordings/s1/line_0_123.m4a');
      expect(recording.durationMs, 5000);
      expect(recording.createdAt, DateTime.utc(2026));
      expect(recording.grade, 3);
    });

    test('grade can be null', () {
      final ungraded = LineRecording(
        id: 'r2',
        scriptId: 's1',
        lineIndex: 0,
        filePath: '/path.m4a',
        durationMs: 1000,
        createdAt: DateTime.utc(2026),
      );
      expect(ungraded.grade, isNull);
    });

    test('equality based on id', () {
      final same = LineRecording(
        id: 'r1',
        scriptId: 'different',
        lineIndex: 99,
        filePath: '/other.m4a',
        durationMs: 0,
        createdAt: DateTime.utc(2000),
      );
      expect(recording, equals(same));
      expect(recording.hashCode, same.hashCode);
    });

    test('inequality with different id', () {
      final different = LineRecording(
        id: 'r99',
        scriptId: 's1',
        lineIndex: 0,
        filePath: '/path.m4a',
        durationMs: 5000,
        createdAt: DateTime.utc(2026),
      );
      expect(recording, isNot(equals(different)));
    });

    test('toJson roundtrip', () {
      final json = recording.toJson();
      final restored = LineRecording.fromJson(json);
      expect(restored.id, recording.id);
      expect(restored.scriptId, recording.scriptId);
      expect(restored.lineIndex, recording.lineIndex);
      expect(restored.filePath, recording.filePath);
      expect(restored.durationMs, recording.durationMs);
      expect(restored.createdAt, recording.createdAt);
      expect(restored.grade, recording.grade);
    });

    test('toJson roundtrip with null grade', () {
      final ungraded = LineRecording(
        id: 'r3',
        scriptId: 's1',
        lineIndex: 0,
        filePath: '/path.m4a',
        durationMs: 1000,
        createdAt: DateTime.utc(2026),
      );
      final json = ungraded.toJson();
      final restored = LineRecording.fromJson(json);
      expect(restored.grade, isNull);
    });
  });
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_core && dart test test/models/line_recording_test.dart
```

Expected: Compilation error.

- [ ] **Step 3: Implement LineRecording**

```dart
import 'package:meta/meta.dart';

/// A voice recording for a specific script line.
@immutable
final class LineRecording {
  /// Creates a [LineRecording].
  const LineRecording({
    required this.id,
    required this.scriptId,
    required this.lineIndex,
    required this.filePath,
    required this.durationMs,
    required this.createdAt,
    this.grade,
  });

  /// Deserializes from a JSON map.
  factory LineRecording.fromJson(Map<String, dynamic> json) => LineRecording(
        id: json['id'] as String,
        scriptId: json['scriptId'] as String,
        lineIndex: json['lineIndex'] as int,
        filePath: json['filePath'] as String,
        durationMs: json['durationMs'] as int,
        createdAt: DateTime.parse(json['createdAt'] as String),
        grade: json['grade'] as int?,
      );

  /// Unique identifier (UUID).
  final String id;

  /// The script this recording belongs to.
  final String scriptId;

  /// Index of the line this recording is for.
  final int lineIndex;

  /// Path to the audio file on disk.
  final String filePath;

  /// Duration in milliseconds.
  final int durationMs;

  /// When this recording was created.
  final DateTime createdAt;

  /// Grade 0-5 (SM-2 quality scale), null if not yet graded.
  final int? grade;

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is LineRecording && id == other.id;

  @override
  int get hashCode => id.hashCode;

  /// Serializes to a JSON-compatible map.
  Map<String, dynamic> toJson() => {
        'id': id,
        'scriptId': scriptId,
        'lineIndex': lineIndex,
        'filePath': filePath,
        'durationMs': durationMs,
        'createdAt': createdAt.toUtc().toIso8601String(),
        'grade': grade,
      };
}
```

- [ ] **Step 4: Export from models.dart**

Add `export 'line_recording.dart';` to `horatio_core/lib/src/models/models.dart`.

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_core && dart test test/models/line_recording_test.dart -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add horatio_core/lib/src/models/line_recording.dart horatio_core/lib/src/models/models.dart horatio_core/test/models/line_recording_test.dart
git commit -m "feat(core): add LineRecording model with JSON serialization"
```

---

### Task 3.2: LineRecordingsTable + Database migration

**Files:**

- Create: `horatio_app/lib/database/tables/line_recordings_table.dart`
- Modify: `horatio_app/lib/database/app_database.dart`

- [ ] **Step 1: Create table definition**

```dart
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
```

- [ ] **Step 2: Update app_database.dart**

Replace the full `app_database.dart` file. Key changes: add `LineRecordingsTable` to tables, bump schema to 2, add migration. Leave `RecordingDao` for Task 3.3.

```dart
import 'package:drift/drift.dart';
import 'package:horatio_app/database/daos/annotation_dao.dart';
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
  daos: [AnnotationDao],
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
```

- [ ] **Step 3: Run codegen**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && dart run build_runner build --delete-conflicting-outputs
```

Expected: Generates updated `.g.dart` files.

- [ ] **Step 4: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test
```

Expected: All pass (in-memory test DB auto-creates all tables).

- [ ] **Step 5: Commit**

```bash
git add horatio_app/lib/database/
git commit -m "feat(db): add LineRecordingsTable and migrate schema v1→v2"
```

---

### Task 3.3: RecordingDao

**Files:**

- Create: `horatio_app/lib/database/daos/recording_dao.dart`
- Modify: `horatio_app/lib/database/app_database.dart` (add DAO reference)
- Create: `horatio_app/test/database/recording_dao_test.dart`

- [ ] **Step 1: Write failing DAO tests**

```dart
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/database/app_database.dart';
import 'package:horatio_app/database/daos/recording_dao.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  late AppDatabase db;
  late RecordingDao dao;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    dao = db.recordingDao;
  });

  tearDown(() => db.close());

  final recording = LineRecording(
    id: 'r1',
    scriptId: 's1',
    lineIndex: 0,
    filePath: '/path/to/file.m4a',
    durationMs: 5000,
    createdAt: DateTime.utc(2026),
  );

  group('RecordingDao', () {
    test('insert and watch recordings', () async {
      await dao.insertRecording('s1', recording);
      final stream = dao.watchRecordingsForScript('s1');
      final recordings = await stream.first;
      expect(recordings, hasLength(1));
      expect(recordings.first.id, 'r1');
      expect(recordings.first.filePath, '/path/to/file.m4a');
    });

    test('delete recording', () async {
      await dao.insertRecording('s1', recording);
      await dao.deleteRecording('r1');
      final recordings = await dao.watchRecordingsForScript('s1').first;
      expect(recordings, isEmpty);
    });

    test('update grade', () async {
      await dao.insertRecording('s1', recording);
      await dao.updateRecordingGrade('r1', 4);
      final recordings = await dao.watchRecordingsForScript('s1').first;
      expect(recordings.first.grade, 4);
    });

    test('update grade to null', () async {
      await dao.insertRecording('s1', recording);
      await dao.updateRecordingGrade('r1', 4);
      await dao.updateRecordingGrade('r1', null);
      final recordings = await dao.watchRecordingsForScript('s1').first;
      expect(recordings.first.grade, isNull);
    });

    test('watch returns empty for unknown script', () async {
      final recordings =
          await dao.watchRecordingsForScript('unknown').first;
      expect(recordings, isEmpty);
    });

    test('recordings ordered by lineIndex', () async {
      final r2 = LineRecording(
        id: 'r2',
        scriptId: 's1',
        lineIndex: 5,
        filePath: '/p2.m4a',
        durationMs: 1000,
        createdAt: DateTime.utc(2026),
      );
      await dao.insertRecording('s1', r2);
      await dao.insertRecording('s1', recording);
      final recordings = await dao.watchRecordingsForScript('s1').first;
      expect(recordings[0].lineIndex, 0);
      expect(recordings[1].lineIndex, 5);
    });
  });
}
```

- [ ] **Step 2: Implement RecordingDao**

```dart
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

  LineRecording _rowToRecording(LineRecordingsTableData row) => LineRecording(
        id: row.id,
        scriptId: row.scriptId,
        lineIndex: row.lineIndex,
        filePath: row.filePath,
        durationMs: row.durationMs,
        createdAt: row.createdAt,
        grade: row.grade,
      );
}
```

- [ ] **Step 3: Add RecordingDao to AppDatabase**

Update `app_database.dart` — add `RecordingDao` to `daos` list:

```dart
@DriftDatabase(
  tables: [
    TextMarksTable,
    LineNotesTable,
    AnnotationSnapshotsTable,
    LineRecordingsTable,
  ],
  daos: [AnnotationDao, RecordingDao],
)
```

Add import: `import 'package:horatio_app/database/daos/recording_dao.dart';`

- [ ] **Step 4: Run codegen**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && dart run build_runner build --delete-conflicting-outputs
```

- [ ] **Step 5: Run tests**

```bash
cd /home/kuhy/testsAndMisc/horatio/horatio_app && flutter test test/database/recording_dao_test.dart -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add horatio_app/lib/database/ horatio_app/test/database/recording_dao_test.dart
git commit -m "feat(db): add RecordingDao with CRUD + stream watch"
```

---

### Task 3.4: Run pipeline for Chunk 3

- [ ] **Step 1: Run codegen + analyze + test**

```bash
cd /home/kuhy/testsAndMisc/horatio && ./run.sh test
```

Expected: 100% coverage.

---
