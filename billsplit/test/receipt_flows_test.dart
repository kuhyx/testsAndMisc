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

  group('receipt screen', () {
    testWidgets('unknown id shows deleted note', (tester) async {
      final s = tempState();
      await pumpApp(tester, s, const ReceiptScreen(receiptId: 'nope'));
      expect(find.text('Receipt deleted.'), findsOneWidget);
    });

    testWidgets('tabs on narrow, panes on wide', (tester) async {
      final s = tempState()..addPerson('Ala');
      demoReceipt(s);
      await pumpApp(tester, s, const ReceiptScreen(receiptId: 'r1'));
      await flushSaves(tester);
      expect(find.byType(TabBar), findsOneWidget);
      await tester.tap(find.text('Totals'));
      await tester.pumpAndSettle();
      expect(find.textContaining('grosz-exact'), findsOneWidget);

      tester.view.physicalSize = const Size(1600, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      await tester.pumpAndSettle();
      expect(find.byType(TabBar), findsNothing);
      expect(find.byType(VerticalDivider), findsOneWidget);
    });

    testWidgets('participants: empty roster snackbar, then editing',
        (tester) async {
      final s = tempState();
      demoReceipt(s);
      await pumpApp(tester, s, const ReceiptScreen(receiptId: 'r1'));
      await flushSaves(tester);
      await tester.tap(find.byIcon(Icons.group));
      await tester.pumpAndSettle();
      expect(find.textContaining('Add people first'), findsOneWidget);

      final p = s.addPerson('Ala');
      s.addPerson('Bob');
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.group));
      await tester.pumpAndSettle();
      expect(find.text('Who is on this receipt?'), findsOneWidget);
      await tester.tap(find.byType(CheckboxListTile).first);
      await tester.pumpAndSettle();
      expect(s.receipts.single.participantIds.contains(p.id), isTrue);
      await tester.tap(find.byType(CheckboxListTile).first);
      await tester.pumpAndSettle();
      await tester.tapAt(const Offset(10, 10));
      await tester.pumpAndSettle();
      await flushSaves(tester);
    });

    testWidgets('export: no participants, success, cancel, failure',
        (tester) async {
      final s = tempState();
      demoReceipt(s);
      await pumpApp(tester, s, const ReceiptScreen(receiptId: 'r1'));
      await flushSaves(tester);

      await tester.tap(find.byIcon(Icons.table_view));
      await tester.pumpAndSettle();
      expect(find.textContaining('Add participants'), findsOneWidget);

      s.addPerson('Ala');
      s.receipts.single.participantIds.addAll(s.people.map((p) => p.id));
      mockFilePicker(saveResult: '/tmp/out.xlsx');
      await tester.pump(const Duration(seconds: 5)); // expire prior snackbar
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.table_view));
      await tester.pumpAndSettle();
      expect(find.textContaining('Saved: out.xlsx'), findsOneWidget);

      mockFilePicker();
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.table_view));
      await tester.pumpAndSettle();

      mockFilePicker(saveThrows: true);
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.table_view));
      await tester.pumpAndSettle();
      expect(find.textContaining('Export failed'), findsOneWidget);
      await flushSaves(tester);
    });
  });
}
