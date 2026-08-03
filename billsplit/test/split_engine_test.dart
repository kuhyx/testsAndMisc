import 'dart:io';
import 'dart:math';

import 'package:billsplit/domain/eparagon_parser.dart';
import 'package:billsplit/domain/models.dart';
import 'package:billsplit/domain/split_engine.dart';
import 'package:flutter_test/flutter_test.dart';

List<Person> makePeople(int n, {Set<int> nonDrinkers = const {}}) => [
      for (var i = 0; i < n; i++)
        Person(id: 'p$i', name: 'P$i', drinks: !nonDrinkers.contains(i)),
    ];

void main() {
  test('splitAmount: exact sum, deterministic, rotation moves the extra', () {
    final shares = splitAmount(100, ['b', 'a', 'c']); // rotation 0
    expect(shares.values.reduce((a, b) => a + b), 100);
    expect(shares['a'], 34); // sorted order, start at index 0
    expect(shares['b'], 33);
    expect(shares['c'], 33);
    final rotated = splitAmount(100, ['b', 'a', 'c'], rotation: 1);
    expect(rotated.values.reduce((a, b) => a + b), 100);
    expect(rotated['b'], 34); // start shifted by one
    // Same inputs -> same output (deterministic).
    expect(splitAmount(100, ['b', 'a', 'c'], rotation: 1), rotated);
  });

  test('splitAmount: negative totals (returns) also sum exactly', () {
    final shares = splitAmount(-100, ['a', 'b', 'c']);
    expect(shares.values.reduce((a, b) => a + b), -100);
    expect(shares.values.every((v) => v == -33 || v == -34), isTrue);
  });

  test('splitAmount fuzz: sum invariant over random cases', () {
    final rnd = Random(42);
    for (var i = 0; i < 500; i++) {
      final n = 1 + rnd.nextInt(9);
      final total = rnd.nextInt(100000) - 5000;
      final ids = List.generate(n, (j) => 'p$j');
      final shares = splitAmount(total, ids, rotation: rnd.nextInt(1000));
      expect(
        shares.values.fold(0, (a, b) => a + b),
        total,
        reason: 'total=$total n=$n',
      );
      final values = shares.values.toList();
      expect(
        values.reduce(max) - values.reduce(min),
        lessThanOrEqualTo(1),
        reason: 'shares differ by more than 1 grosz',
      );
    }
  });

  test('modes resolve correctly and intersect with receipt participants', () {
    final people = makePeople(4, nonDrinkers: {3});
    final group = Group(id: 'g1', name: 'Meat', memberIds: {'p0', 'p2'});
    final receipt = Receipt(
      id: 'r',
      title: 't',
      participantIds: {'p0', 'p1', 'p3'}, // p2 not on this receipt
    );
    Item mk(Assignment a) =>
        Item(id: Ids.next(), name: 'x', totalGr: 300, assignment: a);

    expect(
      resolveParticipants(mk(Assignment()), receipt, people, [group])
          .map((p) => p.id),
      ['p0', 'p1', 'p3'],
    );
    expect(
      resolveParticipants(
        mk(Assignment(mode: AssignMode.drinkers)),
        receipt,
        people,
        [group],
      ).map((p) => p.id),
      ['p0', 'p1'],
    );
    expect(
      resolveParticipants(
        mk(Assignment(mode: AssignMode.nonDrinkers)),
        receipt,
        people,
        [group],
      ).map((p) => p.id),
      ['p3'],
    );
    // Group intersected with receipt pool: p2 excluded.
    expect(
      resolveParticipants(
        mk(Assignment(mode: AssignMode.group, groupId: 'g1')),
        receipt,
        people,
        [group],
      ).map((p) => p.id),
      ['p0'],
    );
    expect(
      resolveParticipants(
        mk(Assignment(mode: AssignMode.custom, customIds: {'p1', 'p2'})),
        receipt,
        people,
        [group],
      ).map((p) => p.id),
      ['p1'],
    );
    // Missing group -> unassigned.
    expect(
      resolveParticipants(
        mk(Assignment(mode: AssignMode.group, groupId: 'gone')),
        receipt,
        people,
        [group],
      ),
      isEmpty,
    );
  });

  test('real receipt: 8 people, all drinkers — reconciles to 597.55', () {
    final receipt = parseEParagon(
      File('test/fixtures/sample_receipt.json').readAsStringSync(),
    );
    final people = makePeople(8);
    receipt.participantIds.addAll(people.map((p) => p.id));

    final split = computeSplit(receipt, people, []);
    expect(split.unassigned, isEmpty);
    // Exact reconciliation is the hard invariant.
    expect(split.assignedTotalGr, 59755);
    // 59755 / 8 = 7469.375 -> everyone lands within a few grosze of that;
    // remainder rotation spreads the extras instead of stacking them on the
    // alphabetically-first person.
    final totals = split.perPerson.values.map((t) => t.totalGr).toList();
    for (final t in totals) {
      expect(t, inInclusiveRange(7469 - 15, 7470 + 15));
    }
    // Alcohol: 79.98 + 28.74 = 108.72 split over 8 -> 13.59 each ±2 gr.
    final alcohol = split.perPerson.values.map((t) => t.alcoholGr).toList();
    expect(alcohol.fold(0, (a, b) => a + b), 10872);
    for (final a in alcohol) {
      expect(a, inInclusiveRange(1357, 1361));
    }
  });

  test('real receipt: 2 non-drinkers pay no alcohol, totals still exact', () {
    final receipt = parseEParagon(
      File('test/fixtures/sample_receipt.json').readAsStringSync(),
    );
    final people = makePeople(8, nonDrinkers: {6, 7});
    receipt.participantIds.addAll(people.map((p) => p.id));

    final split = computeSplit(receipt, people, []);
    expect(split.assignedTotalGr, 59755);
    expect(split.perPerson['p6']!.alcoholGr, 0);
    expect(split.perPerson['p7']!.alcoholGr, 0);
    // 10872 over 6 drinkers = 1812 each ±2 gr, summing exactly.
    final drinkerAlcohol = [
      for (var i = 0; i < 6; i++) split.perPerson['p$i']!.alcoholGr,
    ];
    expect(drinkerAlcohol.fold(0, (a, b) => a + b), 10872);
    for (final a in drinkerAlcohol) {
      expect(a, inInclusiveRange(1810, 1814));
    }
    // Non-drinkers pay strictly less.
    expect(
      split.perPerson['p7']!.totalGr,
      lessThan(split.perPerson['p0']!.totalGr),
    );
  });

  test('items with no possible participants are reported, not lost', () {
    final people = makePeople(2); // both drinkers
    final receipt = Receipt(id: 'r', title: 't', participantIds: {'p0', 'p1'});
    receipt.items.add(
      Item(
        id: 'i1',
        name: 'water',
        totalGr: 500,
        assignment: Assignment(mode: AssignMode.nonDrinkers),
      ),
    );
    receipt.items.add(Item(id: 'i2', name: 'bread', totalGr: 300));

    final split = computeSplit(receipt, people, []);
    expect(split.unassigned.map((i) => i.id), ['i1']);
    expect(split.assignedTotalGr, 300);
  });
}
