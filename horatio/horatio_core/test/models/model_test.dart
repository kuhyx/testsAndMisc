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
}
