import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/services/script_repository.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  group('ScriptRepository', () {
    late ScriptRepository repo;

    setUp(() {
      repo = ScriptRepository();
    });

    test('starts empty', () {
      expect(repo.scripts, isEmpty);
    });

    test('add appends a script', () {
      final script = TextParser().parse(
        title: 'Test',
        content: 'A: Hello.\nB: World.',
      );
      repo.add(script);
      expect(repo.scripts, hasLength(1));
      expect(repo.scripts.first.title, 'Test');
    });

    test('removeAt removes script at index', () {
      final s1 = TextParser().parse(
        title: 'First',
        content: 'A: One.\nB: Two.',
      );
      final s2 = TextParser().parse(
        title: 'Second',
        content: 'C: Three.\nD: Four.',
      );
      repo
        ..add(s1)
        ..add(s2)
        ..removeAt(0);
      expect(repo.scripts, hasLength(1));
      expect(repo.scripts.first.title, 'Second');
    });

    test('clear removes all scripts', () {
      final script = TextParser().parse(
        title: 'Test',
        content: 'A: Hello.\nB: World.',
      );
      repo
        ..add(script)
        ..clear();
      expect(repo.scripts, isEmpty);
    });

    test('scripts returns unmodifiable list', () {
      expect(
        () => repo.scripts.add(
          TextParser().parse(
            title: 'X',
            content: 'A: line.',
          ),
        ),
        throwsA(isA<UnsupportedError>()),
      );
    });
  });
}
