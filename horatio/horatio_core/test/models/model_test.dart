import 'package:horatio_core/horatio_core.dart';
import 'package:test/test.dart';

void main() {
  group('Role', () {
    test('equality compares normalized names', () {
      const a = Role(name: 'Hamlet');
      const b = Role(name: 'hamlet');
      const c = Role(name: 'Ophelia');

      expect(a, equals(b));
      expect(a, isNot(equals(c)));
      expect(a == a, isTrue); // identical
    });

    test('hashCode matches for equal roles', () {
      const a = Role(name: 'Hamlet');
      const b = Role(name: 'HAMLET');
      expect(a.hashCode, b.hashCode);
    });

    test('toString includes name', () {
      const role = Role(name: 'Hamlet');
      expect(role.toString(), 'Role(Hamlet)');
    });
  });

  group('Scene', () {
    test('toString shows title and line count', () {
      const scene = Scene(
        title: 'Act I',
        lines: [
          ScriptLine(
            text: 'Hello',
            role: Role(name: 'A'),
            sceneIndex: 0,
            lineIndex: 0,
          ),
        ],
      );
      expect(scene.toString(), 'Scene(Act I, 1 lines)');
    });

    test('toString shows untitled when no title', () {
      const scene = Scene(lines: []);
      expect(scene.toString(), 'Scene(untitled, 0 lines)');
    });
  });

  group('Script', () {
    const hamlet = Role(name: 'Hamlet');
    const horatio = Role(name: 'Horatio');

    const testScript = Script(
      id: 'test-id',
      title: 'Test',
      roles: [hamlet, horatio],
      scenes: [
        Scene(
          lines: [
            ScriptLine(
              text: 'Line 1',
              role: hamlet,
              sceneIndex: 0,
              lineIndex: 0,
            ),
            ScriptLine(
              text: 'Line 2',
              role: horatio,
              sceneIndex: 0,
              lineIndex: 1,
            ),
            ScriptLine(
              text: 'Line 3',
              role: hamlet,
              sceneIndex: 0,
              lineIndex: 2,
            ),
          ],
        ),
      ],
    );

    test('id field is accessible', () {
      const script = Script(
        id: 'test-uuid-123',
        title: 'Test',
        roles: [],
        scenes: [],
      );
      expect(script.id, 'test-uuid-123');
    });

    test('totalLineCount sums across scenes', () {
      expect(testScript.totalLineCount, 3);
    });

    test('lineCountForRole counts only matching role', () {
      expect(testScript.lineCountForRole(hamlet), 2);
      expect(testScript.lineCountForRole(horatio), 1);
    });

    test('toString includes title, role count, scene count', () {
      expect(testScript.toString(), 'Script(Test, 2 roles, 1 scenes)');
    });
  });

  group('ScriptLine', () {
    test('isStageDirection returns true when role is null', () {
      const direction = ScriptLine.direction(
        text: 'Enter Hamlet',
        sceneIndex: 0,
        lineIndex: 0,
      );
      expect(direction.isStageDirection, isTrue);
    });

    test('isStageDirection returns false for dialogue', () {
      const line = ScriptLine(
        text: 'To be',
        role: Role(name: 'Hamlet'),
        sceneIndex: 0,
        lineIndex: 0,
      );
      expect(line.isStageDirection, isFalse);
    });

    test('toString uses role name for dialogue', () {
      const line = ScriptLine(
        text: 'Short line',
        role: Role(name: 'Hamlet'),
        sceneIndex: 0,
        lineIndex: 0,
      );
      expect(line.toString(), 'ScriptLine(Hamlet: Short line)');
    });

    test('toString truncates long text', () {
      const line = ScriptLine(
        text:
            'This is a very long line of dialogue that exceeds forty characters easily',
        role: Role(name: 'Hamlet'),
        sceneIndex: 0,
        lineIndex: 0,
      );
      expect(line.toString(), contains('...'));
      // Should be 40 chars + "..."
      expect(line.toString(), startsWith('ScriptLine(Hamlet: '));
    });

    test('toString uses DIRECTION for stage directions', () {
      const line = ScriptLine.direction(
        text: 'Exeunt',
        sceneIndex: 0,
        lineIndex: 0,
      );
      expect(line.toString(), 'ScriptLine(DIRECTION: Exeunt)');
    });
  });

  group('SrsCard', () {
    test('isDue returns true when nextReview is at or before now', () {
      final card = SrsCard(
        id: 'c1',
        cueText: 'cue',
        answerText: 'answer',
        nextReview: DateTime(2026, 3, 27),
      );
      expect(card.isDue(now: DateTime(2026, 3, 28)), isTrue);
    });

    test('isDue returns false when nextReview is after now', () {
      final card = SrsCard(
        id: 'c1',
        cueText: 'cue',
        answerText: 'answer',
        nextReview: DateTime(2026, 3, 29),
      );
      expect(card.isDue(now: DateTime(2026, 3, 28)), isFalse);
    });

    test('isDue uses current time when now is omitted', () {
      final card = SrsCard(
        id: 'c1',
        cueText: 'cue',
        answerText: 'answer',
        nextReview: DateTime(2000),
      );
      // A card due in 2000 should definitely be due now.
      expect(card.isDue(), isTrue);
    });

    test('isNew returns true for unreviewed card', () {
      final card = SrsCard(id: 'c1', cueText: 'cue', answerText: 'answer');
      expect(card.isNew, isTrue);
    });

    test('isNew returns false after review', () {
      final card = SrsCard(id: 'c1', cueText: 'cue', answerText: 'answer')
        ..repetitions = 1;
      expect(card.isNew, isFalse);
    });

    test('toString includes id, interval, and ease', () {
      final card = SrsCard(id: 'test', cueText: 'cue', answerText: 'answer');
      expect(card.toString(), contains('SrsCard(test'));
      expect(card.toString(), contains('interval: 1'));
      expect(card.toString(), contains('ease: 2.50'));
    });
  });

  group('StageDirection', () {
    test('toString includes text', () {
      const direction = StageDirection(text: 'Enter Hamlet');
      expect(direction.toString(), 'StageDirection(Enter Hamlet)');
    });
  });

  group('DailySession', () {
    test('totalCards sums new and review', () {
      final session = DailySession(
        date: DateTime(2026, 3, 28),
        newCardCount: 5,
        reviewCardCount: 10,
      );
      expect(session.totalCards, 15);
    });

    test('toString includes date and counts', () {
      final session = DailySession(
        date: DateTime(2026, 3, 28),
        newCardCount: 5,
        reviewCardCount: 10,
      );
      expect(session.toString(), contains('2026-03-28'));
      expect(session.toString(), contains('new: 5'));
      expect(session.toString(), contains('review: 10'));
    });
  });

  group('DiffSegment', () {
    test('toString includes type and text', () {
      const segment = DiffSegment(text: 'hello', type: DiffType.match);
      expect(segment.toString(), 'Diff(match: hello)');
    });
  });

  group('TextMark', () {
    final now = DateTime.utc(2026, 3, 29, 12);

    TextMark makeMark({
      String id = 'mark-1',
      int lineIndex = 0,
      int startOffset = 0,
      int endOffset = 5,
      MarkType type = MarkType.stress,
      DateTime? createdAt,
    }) => TextMark(
      id: id,
      lineIndex: lineIndex,
      startOffset: startOffset,
      endOffset: endOffset,
      type: type,
      createdAt: createdAt ?? now,
    );

    test('construction with valid offsets', () {
      final mark = makeMark();
      expect(mark.id, 'mark-1');
      expect(mark.lineIndex, 0);
      expect(mark.startOffset, 0);
      expect(mark.endOffset, 5);
      expect(mark.type, MarkType.stress);
      expect(mark.createdAt, now);
    });

    test('equality uses id only', () {
      final a = makeMark();
      final b = makeMark(type: MarkType.pause, endOffset: 10);
      final c = makeMark(id: 'mark-2');

      expect(a, equals(b));
      expect(a, isNot(equals(c)));
      expect(a == a, isTrue);
    });

    test('hashCode consistent with equality', () {
      final a = makeMark();
      final b = makeMark(type: MarkType.pause, endOffset: 10);
      expect(a.hashCode, b.hashCode);
    });

    test('assert fails for negative startOffset', () {
      expect(() => makeMark(startOffset: -1), throwsA(isA<AssertionError>()));
    });

    test('assert fails when endOffset <= startOffset', () {
      expect(
        () => makeMark(startOffset: 5, endOffset: 4),
        throwsA(isA<AssertionError>()),
      );
      expect(
        () => makeMark(startOffset: 3, endOffset: 3),
        throwsA(isA<AssertionError>()),
      );
    });

    test('toJson roundtrip', () {
      final original = makeMark();
      final json = original.toJson();
      final restored = TextMark.fromJson(json);

      expect(restored.id, original.id);
      expect(restored.lineIndex, original.lineIndex);
      expect(restored.startOffset, original.startOffset);
      expect(restored.endOffset, original.endOffset);
      expect(restored.type, original.type);
      expect(restored.createdAt, original.createdAt);
    });

    test('fromJson with invalid type throws ArgumentError', () {
      final json = makeMark().toJson()..['type'] = 'invalid';
      expect(() => TextMark.fromJson(json), throwsArgumentError);
    });

    test('toJson serializes all MarkType values', () {
      for (final type in MarkType.values) {
        final mark = makeMark(type: type);
        final json = mark.toJson();
        final restored = TextMark.fromJson(json);
        expect(restored.type, type);
      }
    });
  });

  group('LineNote', () {
    final now = DateTime.utc(2026, 3, 29, 12);

    LineNote makeNote({
      String id = 'note-1',
      int lineIndex = 0,
      NoteCategory category = NoteCategory.intention,
      String text = 'Seeking revenge',
      DateTime? createdAt,
    }) => LineNote(
      id: id,
      lineIndex: lineIndex,
      category: category,
      text: text,
      createdAt: createdAt ?? now,
    );

    test('construction fields accessible', () {
      final note = makeNote();
      expect(note.id, 'note-1');
      expect(note.lineIndex, 0);
      expect(note.category, NoteCategory.intention);
      expect(note.text, 'Seeking revenge');
      expect(note.createdAt, now);
    });

    test('equality uses id only', () {
      final a = makeNote();
      final b = makeNote(
        text: 'Different text',
        category: NoteCategory.subtext,
      );
      final c = makeNote(id: 'note-2');

      expect(a, equals(b));
      expect(a, isNot(equals(c)));
      expect(a == a, isTrue);
    });

    test('hashCode consistent with equality', () {
      final a = makeNote();
      final b = makeNote(text: 'Different', category: NoteCategory.blocking);
      expect(a.hashCode, b.hashCode);
    });

    test('toJson roundtrip', () {
      final original = makeNote();
      final json = original.toJson();
      final restored = LineNote.fromJson(json);

      expect(restored.id, original.id);
      expect(restored.lineIndex, original.lineIndex);
      expect(restored.category, original.category);
      expect(restored.text, original.text);
      expect(restored.createdAt, original.createdAt);
    });

    test('fromJson with invalid category throws ArgumentError', () {
      final json = makeNote().toJson()..['category'] = 'invalid';
      expect(() => LineNote.fromJson(json), throwsArgumentError);
    });

    test('toJson serializes all NoteCategory values', () {
      for (final category in NoteCategory.values) {
        final note = makeNote(category: category);
        final json = note.toJson();
        final restored = LineNote.fromJson(json);
        expect(restored.category, category);
      }
    });
  });

  group('AnnotationSnapshot', () {
    final now = DateTime.utc(2026, 3, 29, 12);

    TextMark sampleMark() => TextMark(
      id: 'mark-snap-1',
      lineIndex: 0,
      startOffset: 0,
      endOffset: 5,
      type: MarkType.stress,
      createdAt: now,
    );

    LineNote sampleNote() => LineNote(
      id: 'note-snap-1',
      lineIndex: 0,
      category: NoteCategory.intention,
      text: 'Seeking revenge',
      createdAt: now,
    );

    test('construction with unmodifiable lists', () {
      final snapshot = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'script-1',
        timestamp: now,
        marks: [sampleMark()],
        notes: [sampleNote()],
      );

      expect(snapshot.marks, hasLength(1));
      expect(snapshot.notes, hasLength(1));
      expect(() => snapshot.marks.add(sampleMark()), throwsUnsupportedError);
      expect(() => snapshot.notes.add(sampleNote()), throwsUnsupportedError);
    });

    test('equality uses id only', () {
      final a = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'script-1',
        timestamp: now,
        marks: const [],
        notes: const [],
      );
      final b = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'different-script',
        timestamp: now.add(const Duration(hours: 1)),
        marks: [sampleMark()],
        notes: [sampleNote()],
      );
      final c = AnnotationSnapshot(
        id: 'snap-2',
        scriptId: 'script-1',
        timestamp: now,
        marks: const [],
        notes: const [],
      );

      expect(a, equals(b));
      expect(a, isNot(equals(c)));
      expect(a == a, isTrue);
    });

    test('hashCode consistent with equality', () {
      final a = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'script-1',
        timestamp: now,
        marks: const [],
        notes: const [],
      );
      final b = AnnotationSnapshot(
        id: 'snap-1',
        scriptId: 'other',
        timestamp: now,
        marks: [sampleMark()],
        notes: const [],
      );
      expect(a.hashCode, b.hashCode);
    });

    test('toJson roundtrip with empty lists', () {
      final original = AnnotationSnapshot(
        id: 'snap-empty',
        scriptId: 'script-1',
        timestamp: now,
        marks: const [],
        notes: const [],
      );
      final json = original.toJson();
      final restored = AnnotationSnapshot.fromJson(json);

      expect(restored.id, original.id);
      expect(restored.scriptId, original.scriptId);
      expect(restored.timestamp, original.timestamp);
      expect(restored.marks, isEmpty);
      expect(restored.notes, isEmpty);
    });

    test('toJson roundtrip with populated lists', () {
      final original = AnnotationSnapshot(
        id: 'snap-full',
        scriptId: 'script-1',
        timestamp: now,
        marks: [sampleMark()],
        notes: [sampleNote()],
      );
      final json = original.toJson();
      final restored = AnnotationSnapshot.fromJson(json);

      expect(restored.id, original.id);
      expect(restored.scriptId, original.scriptId);
      expect(restored.timestamp, original.timestamp);
      expect(restored.marks, hasLength(1));
      expect(restored.marks.first.id, 'mark-snap-1');
      expect(restored.marks.first.type, MarkType.stress);
      expect(restored.notes, hasLength(1));
      expect(restored.notes.first.id, 'note-snap-1');
      expect(restored.notes.first.category, NoteCategory.intention);
    });

    test('fromJson with malformed DateTime throws FormatException', () {
      final json = {
        'id': 'snap-bad',
        'scriptId': 'script-1',
        'timestamp': 'not-a-date',
        'marks': <dynamic>[],
        'notes': <dynamic>[],
      };
      expect(() => AnnotationSnapshot.fromJson(json), throwsFormatException);
    });
  });
}
