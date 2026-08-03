import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:billsplit/domain/models.dart';
import 'package:billsplit/main.dart' as app;
import 'package:billsplit/state/app_state.dart';
import 'package:billsplit/ui/home_screen.dart';
import 'package:billsplit/ui/people_screen.dart';
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
  tearDown(clearChannelMocks);

  group('main()', () {
    testWidgets('boots with the real load path', (tester) async {
      final dir = Directory.systemTemp.createTempSync('billsplit_main');
      addTearDown(() => dir.deleteSync(recursive: true));
      mockPathProvider(dir);
      app.main();
      await tester.pump();
      await tester.pump();
      expect(find.text('BillSplit'), findsOneWidget);
    });
  });

  group('home', () {
    testWidgets('import cancel does nothing', (tester) async {
      mockFilePicker();
      final s = tempState();
      await pumpApp(tester, s, const HomeScreen());
      await tester.tap(find.text('Import e-paragon'));
      await tester.pumpAndSettle();
      expect(s.receipts, isEmpty);
    });

    testWidgets('import parse error shows message', (tester) async {
      mockFilePicker(pickResult: Uint8List.fromList('zzz'.codeUnits));
      final s = tempState();
      await pumpApp(tester, s, const HomeScreen());
      await tester.tap(find.text('Import e-paragon'));
      await tester.pumpAndSettle();
      expect(find.textContaining('neither valid JSON'), findsOneWidget);
      await flushSaves(tester);
    });

    testWidgets('import invalid UTF-8 hits the generic handler',
        (tester) async {
      mockFilePicker(pickResult: Uint8List.fromList([0xFF, 0xFE, 0x00]));
      final s = tempState();
      await pumpApp(tester, s, const HomeScreen());
      await tester.tap(find.text('Import e-paragon'));
      await tester.pumpAndSettle();
      expect(find.textContaining('Import failed'), findsOneWidget);
    });

    testWidgets('import success navigates; warning shows a snackbar',
        (tester) async {
      final fixture =
          File('test/fixtures/sample_receipt.json').readAsBytesSync();
      mockFilePicker(pickResult: fixture);
      final s = tempState()..addPerson('Ala');
      await pumpApp(tester, s, const HomeScreen());
      await tester.tap(find.text('Import e-paragon'));
      await tester.pumpAndSettle();
      expect(s.receipts, hasLength(1));
      expect(find.byType(ReceiptScreen), findsOneWidget);
      await flushSaves(tester);
    });

    testWidgets('import surfaces parser warnings', (tester) async {
      final payload = {
        'dokument': {
          'paragon': {
            'pozycja': [
              {
                'towar': {'nazwa': 'Chleb', 'ilosc': 1, 'brutto': 500},
              },
            ],
            'podsum': {'sumaBrutto': 999},
          },
        },
      };
      final body = base64Url.encode(utf8.encode(jsonEncode(payload)));
      final wrapper = jsonEncode({'data': 'h.$body.s'});
      mockFilePicker(pickResult: Uint8List.fromList(utf8.encode(wrapper)));
      final s = tempState();
      await pumpApp(tester, s, const HomeScreen());
      await tester.tap(find.text('Import e-paragon'));
      await tester.pumpAndSettle();
      expect(find.textContaining('differs'), findsOneWidget);
      await flushSaves(tester);
    });

    testWidgets('manual create: cancel, empty and valid', (tester) async {
      final s = tempState();
      await pumpApp(tester, s, const HomeScreen());

      await tester.tap(find.text('New receipt'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(s.receipts, isEmpty);

      await tester.tap(find.text('New receipt'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Create'));
      await tester.pumpAndSettle();
      expect(s.receipts, isEmpty);

      await tester.tap(find.text('New receipt'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'Pizza night');
      await tester.tap(find.text('Create'));
      await tester.pumpAndSettle();
      expect(s.receipts.single.title, 'Pizza night');
      expect(find.byType(ReceiptScreen), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();

      await tester.tap(find.text('New receipt'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'Kebab');
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pumpAndSettle();
      expect(s.receipts.first.title, 'Kebab');
      await flushSaves(tester);
    });

    testWidgets('list tile navigates; dismiss asks and deletes',
        (tester) async {
      final s = tempState();
      demoReceipt(s);
      await pumpApp(tester, s, const HomeScreen());
      await flushSaves(tester);

      expect(find.textContaining('4 items'), findsOneWidget);
      await tester.tap(find.text('Demo'));
      await tester.pumpAndSettle();
      expect(find.byType(ReceiptScreen), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();

      await tester.drag(find.byType(Dismissible), const Offset(-600, 0));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(s.receipts, hasLength(1));

      await tester.drag(find.byType(Dismissible), const Offset(-600, 0));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Delete'));
      await tester.pumpAndSettle();
      expect(s.receipts, isEmpty);
      await flushSaves(tester);
    });

    testWidgets('people button opens roster', (tester) async {
      final s = tempState();
      await pumpApp(tester, s, const HomeScreen());
      await tester.tap(find.byIcon(Icons.group));
      await tester.pumpAndSettle();
      expect(find.byType(PeopleScreen), findsOneWidget);
    });
  });

  group('people', () {
    testWidgets('add person dialog: toggle, cancel, empty, valid',
        (tester) async {
      final s = tempState();
      await pumpApp(tester, s, const PeopleScreen());
      expect(find.textContaining('Nobody yet'), findsOneWidget);

      await tester.tap(find.text('Add person'));
      await tester.pumpAndSettle();
      await tester.tap(find.byType(Switch));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(s.people, isEmpty);

      await tester.tap(find.text('Add person'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Add'));
      await tester.pumpAndSettle();
      expect(s.people, isEmpty);

      await tester.tap(find.text('Add person'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'Kasia');
      await tester.tap(find.byType(Switch));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Add'));
      await tester.pumpAndSettle();
      expect(s.people.single.name, 'Kasia');
      expect(s.people.single.drinks, isFalse);
      await flushSaves(tester);
    });

    testWidgets('drinks switch, membership early-return, delete flows',
        (tester) async {
      final s = tempState();
      final p = s.addPerson('Ala');
      await pumpApp(tester, s, const PeopleScreen());
      await flushSaves(tester);

      await tester.tap(find.byType(Switch).first);
      await tester.pumpAndSettle();
      expect(p.drinks, isFalse);

      // No groups yet → tapping the person is a no-op branch.
      await tester.tap(find.text('Ala'));
      await tester.pumpAndSettle();
      expect(find.text('Group membership'), findsNothing);

      await tester.tap(find.byIcon(Icons.delete_outline).first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(s.people, hasLength(1));

      await tester.tap(find.byIcon(Icons.delete_outline).first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Remove'));
      await tester.pumpAndSettle();
      expect(s.people, isEmpty);
      await flushSaves(tester);
    });

    testWidgets('groups: add, membership sheet, delete', (tester) async {
      final s = tempState()..addPerson('Ala');
      await pumpApp(tester, s, const PeopleScreen());
      await flushSaves(tester);

      await tester.tap(find.text('Add group'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(s.groups, isEmpty);

      await tester.tap(find.text('Add group'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'Meat');
      await tester.tap(find.text('Add'));
      await tester.pumpAndSettle();
      expect(s.groups.single.name, 'Meat');
      expect(find.textContaining('No members'), findsOneWidget);

      await tester.tap(find.text('Ala'));
      await tester.pumpAndSettle();
      expect(find.byType(CheckboxListTile), findsOneWidget);
      await tester.tap(find.byType(CheckboxListTile));
      await tester.pumpAndSettle();
      expect(s.groups.single.memberIds, hasLength(1));
      await tester.tap(find.byType(CheckboxListTile));
      await tester.pumpAndSettle();
      expect(s.groups.single.memberIds, isEmpty);
      await tester.tapAt(const Offset(10, 10)); // close sheet
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.delete_outline).last);
      await tester.pumpAndSettle();
      expect(s.groups, isEmpty);
      await flushSaves(tester);
    });
  });

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
