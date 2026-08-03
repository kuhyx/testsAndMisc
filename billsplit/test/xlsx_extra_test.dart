import 'dart:io';
import 'dart:typed_data';

import 'package:billsplit/domain/models.dart';
import 'package:billsplit/domain/xlsx_export.dart';
import 'package:billsplit/ui/receipt_screen.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('export handles no store/paid, unassigned items and non-drinkers', () {
    final people = [
      Person(id: 'a', name: 'Ala'),
      Person(id: 'b', name: 'Bob', drinks: false),
    ];
    final receipt = Receipt(
      id: 'r',
      title: 'Manual',
      participantIds: {'a', 'b'},
      items: [
        Item(id: 'i1', name: 'Bread', totalGr: 500),
        Item(
          id: 'i2',
          name: 'Beer',
          totalGr: 300,
          category: Categories.alcohol,
          assignment: Assignment(mode: AssignMode.drinkers),
        ),
        Item(
          id: 'i3',
          name: 'Ghost',
          totalGr: 100,
          assignment: Assignment(mode: AssignMode.custom),
        ),
      ],
    );
    final bytes = exportXlsx(receipt: receipt, roster: people, groups: []);
    expect(bytes.length, greaterThan(1000));
    expect(bytes[0], 0x50);
  });

  // Exercises the REAL disk writer, deliberately as a plain `test` rather than
  // a `testWidgets`: a real dart:io future never completes inside the
  // fake-async zone, which is the whole reason the export flow writes through
  // an injectable seam.
  test('the real export writer puts the bytes on disk', () async {
    final dir = Directory.systemTemp.createTempSync('billsplit_export');
    addTearDown(() => dir.deleteSync(recursive: true));
    final target = '${dir.path}/split.xlsx';
    final payload = Uint8List.fromList([0x50, 0x4B, 0x03, 0x04, 0x99]);

    debugSetExportWriter(null); // restore the real writer
    await writeExport(target, payload, 'application/vnd.ms-excel');

    expect(File(target).readAsBytesSync(), payload);
  });
}
