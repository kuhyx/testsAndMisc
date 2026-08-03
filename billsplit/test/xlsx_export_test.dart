import 'dart:io';

import 'package:billsplit/domain/eparagon_parser.dart';
import 'package:billsplit/domain/models.dart';
import 'package:billsplit/domain/xlsx_export.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('exports a non-trivial xlsx for the real receipt', () {
    final receipt = parseEParagon(
      File('test/fixtures/sample_receipt.json').readAsStringSync(),
    );
    final people = [
      for (var i = 0; i < 8; i++)
        Person(id: 'p$i', name: 'Person ${i + 1}', drinks: i < 6),
    ];
    receipt.participantIds.addAll(people.map((p) => p.id));

    final bytes = exportXlsx(receipt: receipt, roster: people, groups: []);
    expect(bytes.length, greaterThan(4000));
    // PK zip magic.
    expect(bytes[0], 0x50);
    expect(bytes[1], 0x4B);

    // Write out for external validation (recalc via LibreOffice + openpyxl).
    final out = File('build/test_export.xlsx')
      ..createSync(recursive: true)
      ..writeAsBytesSync(bytes);
    expect(out.existsSync(), isTrue);
  });
}
