// People screen flows.


import 'package:billsplit/domain/models.dart';
import 'package:billsplit/state/app_state.dart';
import 'package:billsplit/ui/people_screen.dart';
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
}
