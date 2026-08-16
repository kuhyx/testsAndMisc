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
}
