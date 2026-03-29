import 'package:horatio_core/horatio_core.dart';
import 'package:test/test.dart';

void main() {
  group('LineComparator', () {
    const comparator = LineComparator();

    group('levenshteinDistance', () {
      test('identical strings have distance 0', () {
        expect(comparator.levenshteinDistance('hello', 'hello'), 0);
      });

      test('empty vs non-empty', () {
        expect(comparator.levenshteinDistance('', 'hello'), 5);
        expect(comparator.levenshteinDistance('hello', ''), 5);
      });

      test('single character difference', () {
        expect(comparator.levenshteinDistance('cat', 'bat'), 1);
      });

      test('insertion', () {
        expect(comparator.levenshteinDistance('cat', 'cats'), 1);
      });

      test('deletion', () {
        expect(comparator.levenshteinDistance('cats', 'cat'), 1);
      });
    });

    group('similarity', () {
      test('identical strings return 1.0', () {
        expect(comparator.similarity('to be', 'to be'), 1.0);
      });

      test('completely different strings', () {
        expect(comparator.similarity('abc', 'xyz'), lessThan(0.5));
      });

      test('is case-insensitive', () {
        expect(comparator.similarity('HAMLET', 'hamlet'), 1.0);
      });

      test('both empty returns 1.0', () {
        expect(comparator.similarity('', ''), 1.0);
      });
    });

    group('grade', () {
      test('exact match grades as exact', () {
        expect(
          comparator.grade('To be or not to be', 'to be or not to be'),
          LineMatchGrade.exact,
        );
      });

      test('minor deviation grades as minor', () {
        expect(
          comparator.grade(
            'To be or not to be that is the question',
            "To be or not to be that's the question",
          ),
          LineMatchGrade.minor,
        );
      });

      test('completely wrong grades as missed', () {
        expect(
          comparator.grade(
            'To be or not to be',
            'Something entirely different and unrelated',
          ),
          LineMatchGrade.missed,
        );
      });
    });

    group('wordDiff', () {
      test('matching words marked as match', () {
        final diff = comparator.wordDiff('to be', 'to be');
        expect(diff, hasLength(2));
        expect(diff.every((s) => s.type == DiffType.match), isTrue);
      });

      test('extra words in actual', () {
        final diff = comparator.wordDiff('to be', 'to be or not');
        final extraSegments = diff
            .where((s) => s.type == DiffType.extra)
            .toList();
        expect(extraSegments, isNotEmpty);
      });

      test('missing words from expected', () {
        final diff = comparator.wordDiff('to be or not', 'to be');
        final missingSegments = diff
            .where((s) => s.type == DiffType.missing)
            .toList();
        expect(missingSegments, isNotEmpty);
      });

      test('mismatched words produce missing and extra segments', () {
        final diff = comparator.wordDiff('the cat sat', 'the dog sat');
        // "cat" vs "dog" → one missing, one extra.
        expect(diff.where((s) => s.type == DiffType.missing), isNotEmpty);
        expect(diff.where((s) => s.type == DiffType.extra), isNotEmpty);
        expect(diff.firstWhere((s) => s.type == DiffType.missing).text, 'cat');
        expect(diff.firstWhere((s) => s.type == DiffType.extra).text, 'dog');
      });
    });
  });

  group('MemorizationPlanner', () {
    const planner = MemorizationPlanner();

    Script makeTestScript() {
      const hamlet = Role(name: 'Hamlet');
      const horatio = Role(name: 'Horatio');

      return const Script(
        title: 'Test Script',
        roles: [hamlet, horatio],
        scenes: [
          Scene(
            lines: [
              ScriptLine(
                text: 'My lord, I came to see your funeral.',
                role: horatio,
                sceneIndex: 0,
                lineIndex: 0,
              ),
              ScriptLine(
                text: 'I pray thee, do not mock me, fellow-student.',
                role: hamlet,
                sceneIndex: 0,
                lineIndex: 1,
              ),
              ScriptLine(
                text: 'My lord, my lord!',
                role: horatio,
                sceneIndex: 0,
                lineIndex: 2,
              ),
              ScriptLine(
                text: 'The rest is silence.',
                role: hamlet,
                sceneIndex: 0,
                lineIndex: 3,
              ),
            ],
          ),
        ],
      );
    }

    test('creates cards for chosen role', () {
      final script = makeTestScript();
      const hamlet = Role(name: 'Hamlet');
      final cards = planner.createCards(script: script, role: hamlet);

      expect(cards, hasLength(2));
      expect(
        cards[0].answerText,
        'I pray thee, do not mock me, fellow-student.',
      );
      expect(cards[0].cueText, 'My lord, I came to see your funeral.');
    });

    test('uses preceding line as cue', () {
      final script = makeTestScript();
      const hamlet = Role(name: 'Hamlet');
      final cards = planner.createCards(script: script, role: hamlet);

      // Second hamlet line should be cued by Horatio's preceding line.
      expect(cards[1].cueText, 'My lord, my lord!');
      expect(cards[1].answerText, 'The rest is silence.');
    });

    test('splits long monologues into sentence pairs', () {
      const hamlet = Role(name: 'Hamlet');
      const horatio = Role(name: 'Horatio');

      const script = Script(
        title: 'Monologue Test',
        roles: [hamlet, horatio],
        scenes: [
          Scene(
            lines: [
              ScriptLine(
                text: 'What say you?',
                role: horatio,
                sceneIndex: 0,
                lineIndex: 0,
              ),
              ScriptLine(
                text:
                    'To be, or not to be. That is the question. '
                    'Whether tis nobler in the mind to suffer.',
                role: hamlet,
                sceneIndex: 0,
                lineIndex: 1,
              ),
            ],
          ),
        ],
      );

      final cards = planner.createCards(script: script, role: hamlet);
      // 3 sentences = 3 cards
      expect(cards, hasLength(3));
      expect(cards[0].cueText, 'What say you?');
    });

    group('generateSchedule', () {
      test('distributes cards across days', () {
        final sessions = planner.generateSchedule(
          totalCards: 20,
          startDate: DateTime(2026, 3, 28),
          deadline: DateTime(2026, 4, 7), // 10 days
        );

        expect(sessions, isNotEmpty);
        final totalNew = sessions.fold(0, (sum, s) => sum + s.newCardCount);
        expect(totalNew, 20);
      });

      test('puts all cards in one session if deadline passed', () {
        final sessions = planner.generateSchedule(
          totalCards: 20,
          startDate: DateTime(2026, 3, 28),
          deadline: DateTime(2026, 3, 27),
        );

        expect(sessions, hasLength(1));
        expect(sessions.first.newCardCount, 20);
      });
    });
  });
}
