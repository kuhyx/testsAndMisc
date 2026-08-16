// Receipt item list and assignment sheet flows.

// Receipt screen flows.


import 'package:billsplit/domain/models.dart';
import 'package:billsplit/state/app_state.dart';
import 'package:billsplit/ui/receipt_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

Receipt demoReceipt(AppState s, {bool withUnassigned = false}) {
  final r = Receipt(
    id: 'r1',
    title: 'Demo',
    store: 'Biedronka',
    paidTotalGr: 1000,
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
        name: 'Tonic',
        totalGr: 100,
        category: Categories.mixer,
      ),
      Item(
        id: 'i4',
        name: 'Kaucja',
        totalGr: 100,
        category: Categories.deposit,
      ),
      if (withUnassigned)
        Item(
          id: 'i5',
          name: 'Ghost',
          totalGr: 50,
          assignment: Assignment(mode: AssignMode.custom),
        ),
    ],
  );
  s.addReceipt(r);
  return r;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('receipt items', () {
    testWidgets('items list: labels, unassigned, edit dialog paths',
        (tester) async {
      final s = tempState();
      final p = s.addPerson('Ala');
      s.addPerson('Bob', drinks: false);
      final g = s.addGroup('Meat')..memberIds.add(p.id);
      final r = demoReceipt(s, withUnassigned: true);
      r.items[0].assignment = Assignment(mode: AssignMode.group, groupId: g.id);
      r.items[2].assignment = Assignment(mode: AssignMode.nonDrinkers);
      r.items[3].assignment = Assignment(
        mode: AssignMode.group,
        groupId: 'gone',
      );
      await pumpApp(tester, s, const ReceiptScreen(receiptId: 'r1'));
      await flushSaves(tester);

      expect(find.textContaining('Group: Meat'), findsOneWidget);
      expect(find.textContaining('Group: ?'), findsOneWidget);
      expect(find.textContaining('Drinkers'), findsOneWidget);
      expect(find.textContaining('Non-drinkers'), findsOneWidget);
      expect(find.textContaining('UNASSIGNED'), findsOneWidget);

      await tester.tap(find.text('Totals'));
      await tester.pumpAndSettle();
      expect(find.textContaining('excluded from totals'), findsOneWidget);
      await tester.tap(find.text('Items'));
      await tester.pumpAndSettle();

      // Edit via long-press: invalid total keeps dialog open, then fix+save.
      await tester.longPress(find.text('Bread'));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.widgetWithText(TextField, 'Total (zł)'),
        'abc',
      );
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();
      expect(find.text('Save'), findsOneWidget); // still open
      await tester.enterText(
        find.widgetWithText(TextField, 'Total (zł)'),
        '6,00',
      );
      await tester.enterText(find.widgetWithText(TextField, 'Name'), 'Rolls');
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();
      expect(r.items[0].totalGr, 600);
      expect(r.items[0].name, 'Rolls');

      // Delete an item from the edit dialog.
      await tester.longPress(find.text('Ghost'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Delete'));
      await tester.pumpAndSettle();
      expect(r.items.any((i) => i.name == 'Ghost'), isFalse);

      // Add a new alcohol item via the FAB: cancel first, then create.
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      await tester.enterText(find.widgetWithText(TextField, 'Name'), 'Wine');
      await tester.enterText(
        find.widgetWithText(TextField, 'Total (zł)'),
        '30',
      );
      await tester.tap(find.byType(DropdownButtonFormField<String>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Alcohol').last);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();
      final wine = r.items.singleWhere((i) => i.name == 'Wine');
      expect(wine.totalGr, 3000);
      expect(wine.assignment.mode, AssignMode.drinkers);

      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      await tester.enterText(find.widgetWithText(TextField, 'Name'), 'Chips');
      await tester.enterText(
        find.widgetWithText(TextField, 'Total (zł)'),
        '5',
      );
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();
      expect(
        r.items.singleWhere((i) => i.name == 'Chips').assignment.mode,
        AssignMode.everyone,
      );
      await flushSaves(tester);
    });

    testWidgets('assignment sheet: modes, materialization, nobody',
        (tester) async {
      final s = tempState();
      final ala = s.addPerson('Ala');
      s.addPerson('Bob');
      final g = s.addGroup('Meat')..memberIds.add(ala.id);
      final r = demoReceipt(s);
      await pumpApp(tester, s, const ReceiptScreen(receiptId: 'r1'));
      await flushSaves(tester);

      await tester.tap(find.text('Bread'));
      await tester.pumpAndSettle();
      final item = r.items[0];

      await tester.tap(find.widgetWithText(ChoiceChip, 'Drinkers'));
      await tester.pumpAndSettle();
      expect(item.assignment.mode, AssignMode.drinkers);
      await tester.tap(find.widgetWithText(ChoiceChip, 'Non-drinkers'));
      await tester.pumpAndSettle();
      expect(item.assignment.mode, AssignMode.nonDrinkers);
      expect(find.textContaining('Nobody selected'), findsOneWidget);
      await tester.tap(find.widgetWithText(ChoiceChip, 'Meat'));
      await tester.pumpAndSettle();
      expect(item.assignment.mode, AssignMode.group);
      expect(item.assignment.groupId, g.id);
      await tester.tap(find.widgetWithText(ChoiceChip, 'Everyone'));
      await tester.pumpAndSettle();
      expect(item.assignment.mode, AssignMode.everyone);

      // Toggling a person on a symbolic mode materializes to custom.
      await tester.tap(find.byType(CheckboxListTile).first);
      await tester.pumpAndSettle();
      expect(item.assignment.mode, AssignMode.custom);
      expect(item.assignment.customIds, hasLength(1));
      await tester.tap(find.byType(CheckboxListTile).last);
      await tester.pumpAndSettle();
      expect(item.assignment.customIds, isEmpty);
      expect(find.textContaining('Nobody selected'), findsOneWidget);
      await tester.tap(find.byType(CheckboxListTile).first);
      await tester.pumpAndSettle();
      expect(item.assignment.customIds, hasLength(1));
      await flushSaves(tester);
    });
  });
}
