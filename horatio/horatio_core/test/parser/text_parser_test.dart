import 'package:horatio_core/horatio_core.dart';
import 'package:test/test.dart';

void main() {
  group('TextParser', () {
    late TextParser parser;

    setUp(() {
      parser = TextParser();
    });

    test('parses simple colon-format script', () {
      const script = '''
HAMLET: To be, or not to be, that is the question.
HORATIO: My lord, I came to see your father's funeral.
HAMLET: I pray thee, do not mock me, fellow-student.
''';
      final result = parser.parse(content: script, title: 'Hamlet Excerpt');

      expect(result.title, 'Hamlet Excerpt');
      expect(result.roles, hasLength(2));
      expect(
        result.roles.map((r) => r.name),
        containsAll(['Hamlet', 'Horatio']),
      );
      expect(result.scenes, hasLength(1));
      expect(result.scenes.first.lines, hasLength(3));
    });

    test('parse assigns a non-empty UUID id to the script', () {
      final result = parser.parse(content: 'HAMLET: To be', title: 'Test');
      expect(result.id, isNotEmpty);
      expect(result.id, matches(RegExp(r'^[0-9a-f-]{36}$')));
    });

    test('parses screenplay format with scene headings', () {
      const script = '''
ACT I

HAMLET
To be, or not to be, that is the question.

HORATIO
My lord!

ACT II

HAMLET
The rest is silence.
''';
      final result = parser.parse(content: script, title: 'Hamlet');

      expect(result.scenes, hasLength(2));
      expect(result.scenes[0].title, 'ACT I');
      expect(result.scenes[1].title, 'ACT II');
      expect(result.scenes[0].lines, hasLength(2));
      expect(result.scenes[1].lines, hasLength(1));
    });

    test('handles continuation lines', () {
      const script = '''
HAMLET: To be, or not to be,
that is the question.
Whether 'tis nobler in the mind to suffer.

HORATIO: My lord!
''';
      final result = parser.parse(content: script, title: 'Test');

      expect(
        result.scenes.first.lines.first.text,
        "To be, or not to be, that is the question. Whether 'tis nobler in the mind to suffer.",
      );
    });

    test('handles stage directions', () {
      const script = '''
(Enter HAMLET)
HAMLET: To be, or not to be.
(Exit HAMLET)
''';
      final result = parser.parse(content: script, title: 'Test');
      final lines = result.scenes.first.lines;

      expect(lines[0].isStageDirection, isTrue);
      expect(lines[0].text, 'Enter HAMLET');
      expect(lines[1].isStageDirection, isFalse);
      expect(lines[1].role!.name, 'Hamlet');
      expect(lines[2].isStageDirection, isTrue);
    });

    test('returns empty script for empty input', () {
      final result = parser.parse(content: '', title: 'Empty');
      expect(result.roles, isEmpty);
      expect(result.scenes, hasLength(1));
      expect(result.scenes.first.lines, isEmpty);
    });

    test('detects all unique roles', () {
      const script = '''
HAMLET: Line one.
HORATIO: Line two.
OPHELIA: Line three.
HAMLET: Line four.
''';
      final result = parser.parse(content: script, title: 'Test');
      expect(result.roles, hasLength(3));
    });

    test('calculates line counts per role', () {
      const script = '''
HAMLET: Line one.
HORATIO: Line two.
HAMLET: Line three.
HAMLET: Line four.
''';
      final result = parser.parse(content: script, title: 'Test');
      final hamlet = result.roles.firstWhere((r) => r.name == 'Hamlet');
      expect(result.lineCountForRole(hamlet), 3);
    });
  });
}
