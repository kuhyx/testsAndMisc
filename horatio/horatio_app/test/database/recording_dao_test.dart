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
      final recordings = await dao.watchRecordingsForScript('unknown').first;
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
