import 'dart:convert';

import 'package:billsplit/domain/eparagon_parser.dart';
import 'package:billsplit/domain/models.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> minimalPayload({
  List<dynamic>? pozycja,
  Map<String, dynamic>? extraParagon,
  Map<String, dynamic>? dokumentExtra,
}) {
  return {
    'dokument': {
      ...?dokumentExtra,
      'paragon': {
        if (pozycja != null) 'pozycja': pozycja,
        ...?extraParagon,
      },
    },
  };
}

Map<String, dynamic> towar(String name, int brutto) => {
      'towar': {
        'nazwa': name,
        'ilosc': '1,000',
        'cena': brutto,
        'brutto': brutto,
      },
    };

String asJws(Map<String, dynamic> payload) {
  final body = base64Url.encode(utf8.encode(jsonEncode(payload)));
  return 'eyJh.$body.sig';
}

void main() {
  test('exception toString carries the message', () {
    expect(
      EParagonParseException('boom').toString(),
      'EParagonParseException: boom',
    );
  });

  test('bare JWS with non-map payload is rejected', () {
    final body = base64Url.encode(utf8.encode('123'));
    expect(
      () => parseEParagon('h.$body.s'),
      throwsA(isA<EParagonParseException>()),
    );
  });

  test('three-part token with invalid base64 payload is rejected', () {
    expect(
      () => parseEParagon('aa.§§§.bb'),
      throwsA(isA<EParagonParseException>()),
    );
  });

  test('JSON root that is not a map is rejected', () {
    expect(
      () => parseEParagon('[1, 2]'),
      throwsA(isA<EParagonParseException>()),
    );
  });

  test('wrapper with undecodable data field is rejected', () {
    expect(
      () => parseEParagon('{"data": "a.b"}'),
      throwsA(
        predicate(
          (e) => e is EParagonParseException && e.message.contains('"data"'),
        ),
      ),
    );
  });

  test('missing dokument / paragon / items are rejected with clear messages',
      () {
    expect(
      () => parseEParagon(asJws({'dokument': 1})),
      throwsA(
        predicate(
          (e) => e is EParagonParseException && e.message.contains('dokument'),
        ),
      ),
    );
    expect(
      () => parseEParagon(jsonEncode({'dokument': <String, dynamic>{}})),
      throwsA(
        predicate(
          (e) => e is EParagonParseException && e.message.contains('paragon'),
        ),
      ),
    );
    expect(
      () => parseEParagon(jsonEncode(minimalPayload())),
      throwsA(
        predicate(
          (e) =>
              e is EParagonParseException && e.message.contains('line items'),
        ),
      ),
    );
  });

  test('malformed pozycja entries are skipped, missing brutto warns', () {
    final res = parseEParagonDetailed(
      jsonEncode(
        minimalPayload(
          pozycja: [
            1,
            {'towar': 2},
            {
              'towar': {'nazwa': 'NoPrice', 'ilosc': 'x'},
            },
            {
              'towar': {'nazwa': '  ', 'brutto': 5},
            },
            towar('Chleb', 500),
          ],
        ),
      ),
    );
    expect(res.receipt.items.single.name, 'Chleb');
    expect(res.warnings.single, contains('NoPrice'));
    expect(res.receipt.items.single.qty, 1);
  });

  test('sumaBrutto mismatch produces a warning; paid falls back to sum', () {
    final res = parseEParagonDetailed(
      jsonEncode(
        minimalPayload(
          pozycja: [towar('Chleb', 500)],
          extraParagon: {
            'podsum': {'sumaBrutto': 600},
            'opak': {
              'wart': 100,
              'daneOpak': [
                {'nazwa': 'butelka', 'cena': 50, 'ilosc': 2000},
                {'nazwa': 'zero', 'cena': 50, 'ilosc': 0},
                1,
              ],
            },
          },
        ),
      ),
    );
    expect(res.warnings.single, contains('differs'));
    expect(res.receipt.paidTotalGr, 700); // 600 declared + 100 deposit
    final deposit =
        res.receipt.items.where((i) => i.category == Categories.deposit).single;
    expect(deposit.totalGr, 100);
    expect(deposit.qty, 2);
  });

  test('store aliasing, plain store names and date fallbacks', () {
    final jm = parseEParagon(
      asJws(
        minimalPayload(
          pozycja: [towar('Chleb', 500)],
          dokumentExtra: {
            'podmiot1': {'nazwaPod': ' JERONIMO MARTINS POLSKA S.A. '},
          },
        ),
      ),
    );
    expect(jm.store, 'Biedronka');

    final other = parseEParagon(
      jsonEncode(
        minimalPayload(
          pozycja: [towar('Chleb', 500)],
          dokumentExtra: {
            'podmiot1': {'nazwaPod': 'Żabka'},
            'naglowek': {'dataJPK': '2026-05-01T10:00:00'},
          },
        ),
      ),
    );
    expect(other.store, 'Żabka');
    expect(other.date.year, 2026);
    expect(other.title, contains('Żabka 2026-05-01'));

    final noStore = parseEParagon(
      jsonEncode(
        minimalPayload(
          pozycja: [towar('Chleb', 500)],
          dokumentExtra: {
            'podmiot1': {'nazwaPod': '  '},
          },
        ),
      ),
    );
    expect(noStore.store, isNull);
    expect(noStore.date.year, DateTime.now().year);
  });

  test('quantity and int parsing variants', () {
    final r = parseEParagon(
      jsonEncode(
        minimalPayload(
          pozycja: [
            {
              'towar': {
                'nazwa': 'Ser',
                'ilosc': 2,
                'cena': '100',
                'brutto': 200.4,
              },
            },
            {
              'towar': {'nazwa': 'Mleko', 'ilosc': 'abc', 'brutto': 300},
            },
          ],
        ),
      ),
    );
    expect(r.items[0].qty, 2);
    expect(r.items[0].unitPriceGr, 100);
    expect(r.items[0].totalGr, 200);
    expect(r.items[1].qty, 1);
  });

  test('mixer keyword tagging without alcohol', () {
    final r = parseEParagon(
      jsonEncode(minimalPayload(pozycja: [towar('Tonik cytrynowy', 400)])),
    );
    expect(r.items.single.category, Categories.mixer);
    expect(r.items.single.assignment.mode, AssignMode.everyone);
  });
}
