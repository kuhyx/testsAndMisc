import 'dart:convert';
import 'dart:io';

import 'package:billsplit/domain/models.dart';
import 'package:billsplit/state/app_state.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Directory temp() {
    final d = Directory.systemTemp.createTempSync('billsplit_state');
    addTearDown(() {
      if (d.existsSync()) d.deleteSync(recursive: true);
    });
    return d;
  }

  test('load on a fresh directory yields empty, usable state', () async {
    final s = AppState(overrideDir: temp());
    await s.load();
    expect(s.loaded, isTrue);
    expect(s.people, isEmpty);
    s.dispose();
  });

  test('save/load roundtrip preserves everything', () async {
    final dir = temp();
    final s = AppState(overrideDir: dir);
    await s.load();
    final p = s.addPerson('Ala', drinks: false);
    final g = s.addGroup('Meat')..memberIds.add(p.id);
    s.addReceipt(
      Receipt(
        id: 'r1',
        title: 'T',
        items: [
          Item(
            id: 'i1',
            name: 'x',
            totalGr: 100,
            assignment: Assignment(mode: AssignMode.group, groupId: g.id),
          ),
        ],
      ),
    );
    await s.save();
    s.dispose();

    final s2 = AppState(overrideDir: dir);
    await s2.load();
    expect(s2.people.single.name, 'Ala');
    expect(s2.people.single.drinks, isFalse);
    expect(s2.groups.single.memberIds, {p.id});
    expect(s2.receipts.single.participantIds, {p.id});
    expect(s2.receipts.single.items.single.assignment.groupId, g.id);
    s2.dispose();
  });

  test('load prunes dangling person references', () async {
    final dir = temp();
    File('${dir.path}/billsplit/state.json')
      ..createSync(recursive: true)
      ..writeAsStringSync(
        jsonEncode({
          'people': [
            {'id': 'p1', 'name': 'Ala'},
          ],
          'groups': [
            {
              'id': 'g1',
              'name': 'G',
              'memberIds': ['p1', 'ghost'],
            },
          ],
          'receipts': [
            {
              'id': 'r1',
              'title': 'T',
              'date': '2026-01-01T00:00:00.000',
              'participantIds': ['p1', 'ghost'],
              'items': [
                {
                  'id': 'i1',
                  'name': 'x',
                  'totalGr': 1,
                  'assignment': {
                    'mode': 'custom',
                    'customIds': ['p1', 'ghost'],
                  },
                },
              ],
            },
          ],
        }),
      );
    final s = AppState(overrideDir: dir);
    await s.load();
    expect(s.groups.single.memberIds, {'p1'});
    expect(s.receipts.single.participantIds, {'p1'});
    expect(s.receipts.single.items.single.assignment.customIds, {'p1'});
    s.dispose();
  });

  test('corrupt JSON is survived', () async {
    final dir = temp();
    File('${dir.path}/billsplit/state.json')
      ..createSync(recursive: true)
      ..writeAsStringSync('{oops');
    final s = AppState(overrideDir: dir);
    await s.load();
    expect(s.loaded, isTrue);
    expect(s.people, isEmpty);
    s.dispose();
  });

  test('IO failure on load is survived (billsplit path is a file)', () async {
    final dir = temp();
    File('${dir.path}/billsplit').createSync(recursive: true);
    final s = AppState(overrideDir: dir);
    await s.load();
    expect(s.loaded, isTrue);
    s.dispose();
  });

  test('IO failure on save is survived (state.json is a directory)', () async {
    final dir = temp();
    Directory('${dir.path}/billsplit/state.json').createSync(recursive: true);
    final s = AppState(overrideDir: dir);
    await s.save(); // must not throw
    s.dispose();
  });

  test('mutations debounce into a save', () async {
    final dir = temp();
    final s = AppState(overrideDir: dir);
    await s.load();
    s.addPerson('Ala');
    expect(File('${dir.path}/billsplit/state.json').existsSync(), isFalse);
    await Future<void>.delayed(const Duration(milliseconds: 600));
    expect(File('${dir.path}/billsplit/state.json').existsSync(), isTrue);
    s.dispose();
  });

  test('removePerson / removeGroup fallback / removeReceipt', () async {
    final s = AppState(overrideDir: temp());
    await s.load();
    final p = s.addPerson('Ala');
    final g = s.addGroup('G')..memberIds.add(p.id);
    final item = Item(
      id: 'i1',
      name: 'x',
      totalGr: 1,
      assignment: Assignment(mode: AssignMode.group, groupId: g.id),
    );
    final r = Receipt(id: 'r1', title: 'T', items: [item]);
    s
      ..addReceipt(r)
      ..removeGroup(g);
    expect(item.assignment.mode, AssignMode.everyone);
    expect(item.assignment.groupId, isNull);

    s.removePerson(p);
    expect(r.participantIds, isEmpty);

    s.removeReceipt(r);
    expect(s.receipts, isEmpty);
    s.dispose();
  });

  test('default documents dir is used when no override is given', () async {
    final dir = temp();
    mockPathProvider(dir);
    addTearDown(clearChannelMocks);
    final s = AppState();
    await s.load();
    s.addPerson('Ala');
    await s.save();
    expect(File('${dir.path}/billsplit/state.json').existsSync(), isTrue);
    s.dispose();
  });
}
