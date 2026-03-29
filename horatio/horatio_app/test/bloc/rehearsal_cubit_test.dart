import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/bloc/rehearsal/rehearsal_cubit.dart';
import 'package:horatio_app/bloc/rehearsal/rehearsal_state.dart';
import 'package:horatio_core/horatio_core.dart';

/// Helper to build a script with dialogue.
Script _twoLineScript() {
  final parser = TextParser();
  return parser.parse(
    title: 'Test',
    content: 'HAMLET: To be, or not to be.\n'
        'HORATIO: My lord, I came to see your wedding.\n'
        'HAMLET: Thrift, thrift, Horatio.\n',
  );
}

void main() {
  group('RehearsalCubit', () {
    late Script script;
    late Role hamlet;
    late Role horatio;

    setUp(() {
      script = _twoLineScript();
      hamlet = script.roles.firstWhere((r) => r.name == 'Hamlet');
      horatio = script.roles.firstWhere((r) => r.name == 'Horatio');
    });

    blocTest<RehearsalCubit, RehearsalState>(
      'start emits AwaitingLine for first dialogue pair',
      build: () => RehearsalCubit(script: script, selectedRole: horatio),
      act: (cubit) => cubit.start(),
      expect: () => [
        isA<RehearsalAwaitingLine>()
            .having((s) => s.lineIndex, 'lineIndex', 0)
            .having((s) => s.totalLines, 'totalLines', 1)
            .having((s) => s.cueSpeaker, 'cueSpeaker', 'Hamlet'),
      ],
    );

    blocTest<RehearsalCubit, RehearsalState>(
      'start emits Complete when no dialogue pairs exist',
      build: () {
        // A script where the only role's line has no preceding cue.
        const role = Role(name: 'Solo');
        const s = Script(
          title: 'Empty',
          roles: [role],
          scenes: [
            Scene(
              lines: [
                ScriptLine(
                  text: 'I am alone.',
                  role: role,
                  sceneIndex: 0,
                  lineIndex: 0,
                ),
              ],
            ),
          ],
        );
        return RehearsalCubit(script: s, selectedRole: role);
      },
      act: (cubit) => cubit.start(),
      expect: () => [
        isA<RehearsalComplete>()
            .having((s) => s.totalLines, 'totalLines', 0),
      ],
    );

    blocTest<RehearsalCubit, RehearsalState>(
      'submitLine emits Feedback with grade and diff',
      build: () => RehearsalCubit(script: script, selectedRole: horatio),
      act: (cubit) {
        cubit
          ..start()
          ..submitLine('My lord, I came to see your wedding.');
      },
      expect: () => [
        isA<RehearsalAwaitingLine>(),
        isA<RehearsalFeedback>()
            .having((s) => s.grade, 'grade', LineMatchGrade.exact)
            .having((s) => s.lineIndex, 'lineIndex', 0),
      ],
    );

    blocTest<RehearsalCubit, RehearsalState>(
      'submitLine does nothing when past end',
      build: () => RehearsalCubit(script: script, selectedRole: horatio),
      act: (cubit) {
        cubit
          ..start()
          ..submitLine('correct')
          ..nextLine() // completes because only 1 pair
          ..submitLine('should be ignored');
      },
      expect: () => [
        isA<RehearsalAwaitingLine>(),
        isA<RehearsalFeedback>(),
        isA<RehearsalComplete>(),
      ],
    );

    blocTest<RehearsalCubit, RehearsalState>(
      'nextLine emits AwaitingLine for next pair or Complete',
      build: () => RehearsalCubit(script: script, selectedRole: hamlet),
      act: (cubit) {
        cubit
          ..start()
          // Hamlet has 1 pair: cue=HORATIO line, expected=HAMLET second line
          ..submitLine('Thrift, thrift, Horatio.')
          ..nextLine(); // Should complete
      },
      expect: () => [
        isA<RehearsalAwaitingLine>(),
        isA<RehearsalFeedback>(),
        isA<RehearsalComplete>()
            .having((s) => s.exactCount, 'exact', 1),
      ],
    );

    blocTest<RehearsalCubit, RehearsalState>(
      'tracks all grade categories in completion',
      build: () {
        // Build a script with multiple dialogue pairs for hamlet.
        final parser = TextParser();
        final s = parser.parse(
          title: 'Multi',
          content: 'OTHER: Line one.\n'
              'HERO: Reply one.\n'
              'OTHER: Line two.\n'
              'HERO: Reply two.\n'
              'OTHER: Line three.\n'
              'HERO: Reply three.\n'
              'OTHER: Line four.\n'
              'HERO: Reply four.\n',
        );
        final role = s.roles.firstWhere((r) => r.name == 'Hero');
        return RehearsalCubit(script: s, selectedRole: role);
      },
      act: (cubit) {
        cubit
          ..start()
          // exact
          ..submitLine('Reply one.')
          ..nextLine()
          // minor deviation
          ..submitLine('Reply two')
          ..nextLine()
          // major deviation
          ..submitLine('Something completely different three.')
          ..nextLine()
          // missed
          ..submitLine('')
          ..nextLine();
      },
      expect: () => [
        isA<RehearsalAwaitingLine>(), // line 0
        isA<RehearsalFeedback>(), // exact
        isA<RehearsalAwaitingLine>(), // line 1
        isA<RehearsalFeedback>(), // minor
        isA<RehearsalAwaitingLine>(), // line 2
        isA<RehearsalFeedback>(), // major
        isA<RehearsalAwaitingLine>(), // line 3
        isA<RehearsalFeedback>(), // missed
        isA<RehearsalComplete>(),
      ],
    );

    blocTest<RehearsalCubit, RehearsalState>(
      'skips stage directions when finding cue',
      build: () {
        final parser = TextParser();
        final s = parser.parse(
          title: 'Directions',
          content: 'KING: Speak, Hamlet.\n'
              '(The ghost appears.)\n'
              'HAMLET: I will.\n',
        );
        final role = s.roles.firstWhere((r) => r.name == 'Hamlet');
        return RehearsalCubit(script: s, selectedRole: role);
      },
      act: (cubit) => cubit.start(),
      expect: () => [
        isA<RehearsalAwaitingLine>()
            .having(
              (s) => s.cueSpeaker,
              'cueSpeaker skips direction',
              'King',
            )
            .having((s) => s.cueText, 'cueText', 'Speak, Hamlet.'),
      ],
    );

    test('state classes have correct Equatable props', () {
      const initial = RehearsalInitial();
      expect(initial.props, isEmpty);

      const awaiting = RehearsalAwaitingLine(
        cueText: 'cue',
        cueSpeaker: 'speaker',
        expectedLine: 'line',
        lineIndex: 0,
        totalLines: 5,
      );
      expect(awaiting.props, hasLength(5));

      const feedback = RehearsalFeedback(
        expectedLine: 'exp',
        actualLine: 'act',
        grade: LineMatchGrade.exact,
        diffSegments: [],
        lineIndex: 0,
        totalLines: 1,
      );
      expect(feedback.props, hasLength(6));

      const complete = RehearsalComplete(
        totalLines: 10,
        exactCount: 5,
        minorCount: 3,
        majorCount: 1,
        missedCount: 1,
      );
      expect(complete.props, hasLength(5));
    });
  });
}
