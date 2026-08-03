import 'dart:io';

import 'package:billsplit/domain/eparagon_parser.dart';
import 'package:billsplit/domain/models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final fixture = File('test/fixtures/sample_receipt.json').readAsStringSync();

  test('parses the real Biedronka e-paragon wrapper', () {
    final res = parseEParagonDetailed(fixture);
    final r = res.receipt;

    // 49 goods lines + 1 deposit line.
    expect(r.items.length, 50);
    final deposit =
        r.items.where((i) => i.category == Categories.deposit).toList();
    expect(deposit.length, 1);
    expect(deposit.single.totalGr, 700);
    expect(deposit.single.qty, 14);

    // Goods sum matches receipt sumaBrutto; paid total includes deposit.
    final goods = r.items
        .where((i) => i.category != Categories.deposit)
        .fold(0, (s, i) => s + i.totalGr);
    expect(goods, 59055);
    expect(r.paidTotalGr, 59755);
    expect(res.warnings, isEmpty);

    // Alcohol detection: exactly vodka + beer, drinkers-only by default.
    final alcohol =
        r.items.where((i) => i.category == Categories.alcohol).toList();
    expect(alcohol.length, 2);
    expect(
      alcohol.map((i) => i.name).join(' | ').toLowerCase(),
      allOf(contains('wódka'), contains('piwo')),
    );
    for (final a in alcohol) {
      expect(a.assignment.mode, AssignMode.drinkers);
    }
    expect(alcohol.fold(0, (s, i) => s + i.totalGr), 10872);

    // Mixers tagged but split among everyone.
    final mixers =
        r.items.where((i) => i.category == Categories.mixer).toList();
    expect(mixers.length, greaterThanOrEqualTo(4));
    for (final m in mixers) {
      expect(m.assignment.mode, AssignMode.everyone);
    }

    // Name cleanup: VAT letter stripped, spaces collapsed.
    expect(r.items.first.name, 'Tonic');
    // Weight-based quantity with comma decimal.
    final kielbasa =
        r.items.firstWhere((i) => i.name.startsWith('KiełbBrocka'));
    expect(kielbasa.qty, closeTo(0.871, 1e-9));
    // Discount captured (vodka -28.00).
    final vodka = r.items.firstWhere((i) => i.name.startsWith('WódkaB'));
    expect(vodka.discountGr, -2800);
    expect(vodka.totalGr, 7998);
  });

  test('accepts bare JPK payload and bare JWS token', () {
    final res = parseEParagonDetailed(fixture);
    expect(res.receipt.items, isNotEmpty);
    // Raw JWS from the wrapper should parse identically.
    final jws = RegExp('"data":"([^"]+)"').firstMatch(fixture)!.group(1)!;
    final fromJws = parseEParagon(jws);
    expect(fromJws.items.length, res.receipt.items.length);
  });

  test('rejects garbage input with a clear error', () {
    expect(
      () => parseEParagon('not json'),
      throwsA(isA<EParagonParseException>()),
    );
    expect(
      () => parseEParagon('{"foo": 1}'),
      throwsA(isA<EParagonParseException>()),
    );
  });
}
