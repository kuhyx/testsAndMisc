import 'package:horatio_core/horatio_core.dart';
import 'package:test/test.dart';

void main() {
  group('RoleDetector', () {
    const detector = RoleDetector();

    group('colon format', () {
      test('detects simple colon format', () {
        final result = detector.detectRole('HAMLET: To be, or not to be.');
        expect(result, isNotNull);
        expect(result!.role.name, 'Hamlet');
        expect(result.dialogue, 'To be, or not to be.');
      });

      test('detects multi-word character name', () {
        final result = detector.detectRole('LADY MACBETH: Out, damned spot!');
        expect(result, isNotNull);
        expect(result!.role.name, 'Lady Macbeth');
        expect(result.dialogue, 'Out, damned spot!');
      });

      test('handles empty dialogue after colon', () {
        final result = detector.detectRole('HAMLET:');
        expect(result, isNotNull);
        expect(result!.role.name, 'Hamlet');
        expect(result.dialogue, isEmpty);
      });
    });

    group('bracketed format', () {
      test('detects bracketed character', () {
        final result = detector.detectRole(
          '[OPHELIA] Good my lord, how does your honour?',
        );
        expect(result, isNotNull);
        expect(result!.role.name, 'Ophelia');
        expect(result.dialogue, 'Good my lord, how does your honour?');
      });
    });

    group('screenplay format (all caps standalone)', () {
      test('detects standalone character name', () {
        final result = detector.detectRole('HAMLET');
        expect(result, isNotNull);
        expect(result!.role.name, 'Hamlet');
        expect(result.dialogue, isEmpty);
      });

      test('detects name with trailing space', () {
        final result = detector.detectRole('HORATIO   ');
        expect(result, isNotNull);
        expect(result!.role.name, 'Horatio');
      });
    });

    group('parenthetical format', () {
      test('detects character with stage direction', () {
        final result = detector.detectRole(
          'HAMLET (aside) What a piece of work is man.',
        );
        expect(result, isNotNull);
        expect(result!.role.name, 'Hamlet');
        expect(result.direction, isNotNull);
        expect(result.direction!.text, 'aside');
        expect(result.dialogue, 'What a piece of work is man.');
      });
    });

    group('exclusions', () {
      test('excludes ACT headings', () {
        expect(detector.detectRole('ACT'), isNull);
      });

      test('excludes SCENE headings', () {
        expect(detector.detectRole('SCENE'), isNull);
      });

      test('excludes PROLOGUE', () {
        expect(detector.detectRole('PROLOGUE'), isNull);
      });

      test('ignores single-character names', () {
        expect(detector.detectRole('X'), isNull);
      });

      test('ignores empty lines', () {
        expect(detector.detectRole(''), isNull);
        expect(detector.detectRole('   '), isNull);
      });
    });

    group('stage directions', () {
      test('detects parenthesized stage direction', () {
        final result = detector.detectStageDirection('(Enter HAMLET)');
        expect(result, isNotNull);
        expect(result!.text, 'Enter HAMLET');
      });

      test('detects bracketed stage direction', () {
        final result = detector.detectStageDirection('[Exit all]');
        expect(result, isNotNull);
        expect(result!.text, 'Exit all');
      });

      test('returns null for regular lines', () {
        expect(detector.detectStageDirection('Just some text'), isNull);
      });

      test('extracts embedded stage direction from colon-format dialogue', () {
        final result = detector.detectRole(
          'HAMLET: I am (sighing deeply) very tired.',
        );
        expect(result, isNotNull);
        expect(result!.role.name, 'Hamlet');
        expect(result.direction, isNotNull);
        expect(result.direction!.text, 'sighing deeply');
        // The direction should be stripped from dialogue.
        expect(result.dialogue, isNot(contains('sighing deeply')));
      });
    });
  });
}
