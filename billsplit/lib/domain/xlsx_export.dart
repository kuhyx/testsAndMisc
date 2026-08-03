/// Exports a receipt + computed split to an .xlsx workbook whose layout
/// mirrors the hand-made "podzial_rachunku" sheet: one row per item, a 1/0
/// person matrix, per-item cost-per-person, and a per-person summary.
///
/// Values are written as computed numbers (grosz-exact, matching the in-app
/// engine), plus live SUM formulas for the column totals so the sheet stays
/// consistent when opened in Excel/LibreOffice.
library;

import 'package:billsplit/domain/models.dart';
import 'package:billsplit/domain/split_engine.dart';
import 'package:excel/excel.dart';

/// Renders [receipt] with its current split into xlsx bytes.
List<int> exportXlsx({
  required Receipt receipt,
  required List<Person> roster,
  required List<Group> groups,
}) {
  final excel = Excel.createExcel()..rename('Sheet1', 'Split');
  final sheet = excel['Split'];

  final people = receiptParticipants(receipt, roster)
    ..sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
  final split = computeSplit(receipt, roster, groups);

  final bold = CellStyle(bold: true);
  final boldGrey = CellStyle(
    bold: true,
    backgroundColorHex: ExcelColor.fromHexString('#D9D9D9'),
  );
  final alcoholStyle =
      CellStyle(backgroundColorHex: ExcelColor.fromHexString('#FCE4D6'));
  final warnStyle = CellStyle(
    bold: true,
    backgroundColorHex: ExcelColor.fromHexString('#FFC7CE'),
  );

  void put(int col, int row, CellValue value, [CellStyle? style]) {
    final index = CellIndex.indexByColumnRow(columnIndex: col, rowIndex: row);
    final cell = sheet.cell(index)..value = value;
    if (style != null) cell.cellStyle = style;
  }

  double zl(int gr) => gr / 100.0;

  var r = 0;
  put(0, r, TextCellValue(receipt.title), bold);
  r++;
  put(
    0,
    r,
    TextCellValue(
      [
        if (receipt.store != null) receipt.store!,
        receipt.date.toIso8601String().substring(0, 10),
        if (receipt.paidTotalGr != null)
          'paid ${formatPln(receipt.paidTotalGr!)}',
      ].join(' · '),
    ),
  );
  r += 2;

  // Header row.
  const fixed = ['Lp', 'Item', 'Category', 'Qty', 'Unit', 'Discount', 'Total'];
  for (var c = 0; c < fixed.length; c++) {
    put(c, r, TextCellValue(fixed[c]), boldGrey);
  }
  const p0 = 7;
  for (var i = 0; i < people.length; i++) {
    put(p0 + i, r, TextCellValue(people[i].name), boldGrey);
  }
  put(p0 + people.length, r, TextCellValue('People on item'), boldGrey);
  put(p0 + people.length + 1, r, TextCellValue('Cost / person'), boldGrey);
  r++;

  final firstDataRow = r;
  var lp = 1;
  for (final item in receipt.items) {
    final shares = split.itemShares[item.id] ?? const <String, int>{};
    final isAlcohol = item.category == Categories.alcohol;
    final rowStyle = shares.isEmpty
        ? warnStyle
        : isAlcohol
            ? alcoholStyle
            : null;
    put(0, r, IntCellValue(lp++), rowStyle);
    put(1, r, TextCellValue(item.name), rowStyle);
    put(2, r, TextCellValue(item.category), rowStyle);
    put(3, r, DoubleCellValue(item.qty), rowStyle);
    put(4, r, DoubleCellValue(zl(item.unitPriceGr)), rowStyle);
    put(5, r, DoubleCellValue(zl(item.discountGr)), rowStyle);
    put(6, r, DoubleCellValue(zl(item.totalGr)), rowStyle);
    for (var i = 0; i < people.length; i++) {
      put(
        p0 + i,
        r,
        IntCellValue(shares.containsKey(people[i].id) ? 1 : 0),
        rowStyle,
      );
    }
    put(p0 + people.length, r, IntCellValue(shares.length), rowStyle);
    if (shares.isNotEmpty) {
      // Representative value; the exact grosz split may differ by ±0.01
      // between people — the summary uses the exact per-person numbers.
      put(
        p0 + people.length + 1,
        r,
        DoubleCellValue(zl((item.totalGr / shares.length).round())),
        rowStyle,
      );
    } else {
      put(p0 + people.length + 1, r, TextCellValue('UNASSIGNED'), warnStyle);
    }
    r++;
  }
  final lastDataRow = r - 1;

  // Totals row with a live formula over the Total column.
  put(1, r, TextCellValue('TOTAL'), bold);
  final totalCol = colName(6);
  put(
    6,
    r,
    FormulaCellValue(
      'SUM($totalCol${firstDataRow + 1}:$totalCol${lastDataRow + 1})',
    ),
    bold,
  );
  r += 2;

  // Per-person summary (exact grosz numbers from the engine).
  put(1, r, TextCellValue('SUMMARY'), bold);
  r++;
  put(1, r, TextCellValue('Person'), boldGrey);
  put(2, r, TextCellValue('Owes'), boldGrey);
  put(3, r, TextCellValue('of which alcohol'), boldGrey);
  put(4, r, TextCellValue('rest'), boldGrey);
  r++;
  final firstSummaryRow = r;
  for (final p in people) {
    final t = split.perPerson[p.id];
    put(1, r, TextCellValue(p.name + (p.drinks ? '' : ' (non-drinker)')));
    put(2, r, DoubleCellValue(zl(t?.totalGr ?? 0)));
    put(3, r, DoubleCellValue(zl(t?.alcoholGr ?? 0)));
    put(4, r, DoubleCellValue(zl(t?.restGr ?? 0)));
    r++;
  }
  put(1, r, TextCellValue('SUM'), bold);
  for (var c = 2; c <= 4; c++) {
    final col = colName(c);
    put(c, r, FormulaCellValue('SUM($col$firstSummaryRow:$col$r)'), bold);
  }
  r += 2;

  // Reconciliation note.
  final assigned = split.assignedTotalGr;
  final itemsTotal = receipt.itemsTotalGr;
  put(
    1,
    r,
    TextCellValue(
      _checkLine(receipt, assigned, itemsTotal, split),
    ),
    split.unassigned.isEmpty && assigned == itemsTotal ? bold : warnStyle,
  );
  r += 2;
  put(
    0,
    r,
    TextCellValue(
      '1 = person shares the item. Matrix and summary are exported values '
      'from the app (grosz-exact); edit splits in the app, not here.',
    ),
  );

  // Column widths.
  sheet
    ..setColumnWidth(0, 5)
    ..setColumnWidth(1, 34)
    ..setColumnWidth(2, 11);
  for (var c = 3; c < 7; c++) {
    sheet.setColumnWidth(c, 10);
  }
  for (var i = 0; i < people.length + 2; i++) {
    sheet.setColumnWidth(p0 + i, 12);
  }

  return excel.encode()!;
}

String _checkLine(
  Receipt receipt,
  int assigned,
  int itemsTotal,
  SplitResult split,
) {
  final paid = receipt.paidTotalGr;
  final paidPart = paid == null ? '' : ' / paid ${formatPln(paid)}';
  final un = split.unassigned.length;
  final unPart = un == 0 ? '' : ' — $un UNASSIGNED item(s) excluded';
  return 'Check: assigned ${formatPln(assigned)} '
      '/ items ${formatPln(itemsTotal)}$paidPart$unPart';
}

/// Converts a 0-based column index into its A1-style name (0 → A, 26 → AA).
String colName(int index) {
  var i = index;
  var s = '';
  while (i >= 0) {
    s = String.fromCharCode(65 + (i % 26)) + s;
    i = i ~/ 26 - 1;
  }
  return s;
}
