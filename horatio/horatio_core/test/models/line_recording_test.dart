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
