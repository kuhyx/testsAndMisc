import 'package:billsplit/domain/models.dart';
import 'package:billsplit/domain/xlsx_export.dart';
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
}
