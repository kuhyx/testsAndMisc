import 'package:billsplit/domain/split_engine.dart';
import 'package:billsplit/domain/xlsx_export.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('splitAmount with no people returns empty', () {
    expect(splitAmount(100, const []), isEmpty);
  });

  test('splitAmount accepts negative rotation', () {
    final s = splitAmount(10, ['a', 'b', 'c'], rotation: -1);
    expect(s.values.fold(0, (x, y) => x + y), 10);
  });

  test('stableHash is stable and differs between strings', () {
    expect(stableHash(''), 0);
    expect(stableHash('abc'), stableHash('abc'));
    expect(stableHash('abc'), isNot(stableHash('abd')));
  });

  test('colName covers single and multi letter columns', () {
    expect(colName(0), 'A');
    expect(colName(25), 'Z');
    expect(colName(26), 'AA');
    expect(colName(27), 'AB');
    expect(colName(701), 'ZZ');
    expect(colName(702), 'AAA');
  });
}
