import 'dart:convert';

import 'package:billsplit/domain/models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('formatPln handles zero, cents padding and negatives', () {
    expect(formatPln(0), '0,00 zł');
    expect(formatPln(5), '0,05 zł');
    expect(formatPln(123456), '1234,56 zł');
    expect(formatPln(-7), '-0,07 zł');
  });

  test('Ids are unique and ordered enough', () {
    final a = Ids.next();
    final b = Ids.next();
    expect(a, isNot(b));
  });

  test('Person/Group/Assignment/Item/Receipt JSON roundtrips', () {
    final p = Person(id: 'p1', name: 'Ala', drinks: false);
    expect(Person.fromJson(p.toJson()).drinks, isFalse);

    final g = Group(id: 'g1', name: 'Meat', memberIds: {'p1'});
    expect(Group.fromJson(g.toJson()).memberIds, {'p1'});

    final a = Assignment(mode: AssignMode.group, groupId: 'g1');
    final a2 = Assignment.fromJson(a.toJson());
    expect(a2.mode, AssignMode.group);
    expect(a2.groupId, 'g1');

    final i = Item(
      id: 'i1',
      name: 'Piwo',
      totalGr: 500,
      qty: 2,
      unitPriceGr: 250,
      discountGr: -100,
      category: Categories.alcohol,
      assignment: Assignment(mode: AssignMode.custom, customIds: {'p1'}),
    );
    final i2 = Item.fromJson(
      jsonDecode(jsonEncode(i.toJson())) as Map<String, dynamic>,
    );
    expect(i2.assignment.customIds, {'p1'});
    expect(i2.discountGr, -100);

    final r = Receipt(
      id: 'r1',
      title: 't',
      store: 's',
      items: [i],
      participantIds: {'p1'},
      paidTotalGr: 500,
    );
    final r2 = Receipt.fromJson(
      jsonDecode(jsonEncode(r.toJson())) as Map<String, dynamic>,
    );
    expect(r2.itemsTotalGr, 500);
    expect(r2.participantIds, {'p1'});
    expect(r2.store, 's');
  });

  test('fromJson tolerates missing optional fields', () {
    final p = Person.fromJson(const {'id': 'x', 'name': 'n'});
    expect(p.drinks, isTrue);
    final g = Group.fromJson(const {'id': 'x', 'name': 'n'});
    expect(g.memberIds, isEmpty);
    final a = Assignment.fromJson(const {});
    expect(a.mode, AssignMode.everyone);
    final i = Item.fromJson(const {'id': 'x', 'name': 'n', 'totalGr': 1});
    expect(i.qty, 1);
    expect(i.category, Categories.general);
    final r = Receipt.fromJson(const {'id': 'x', 'title': 't', 'date': 'bad'});
    expect(r.items, isEmpty);
    expect(r.paidTotalGr, isNull);
  });
}
