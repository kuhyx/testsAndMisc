import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:billsplit/domain/models.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

/// Single source of truth: roster, groups, receipts. Persisted as one JSON
/// file in the app documents directory; saves are debounced.
class AppState extends ChangeNotifier {
  /// Creates the state; [overrideDir] replaces the platform documents
  /// directory (used by tests).
  AppState({Directory? overrideDir}) : _overrideDir = overrideDir;

  final Directory? _overrideDir;

  /// The shared roster of people.
  final List<Person> people = [];

  /// User-defined groups over [people].
  final List<Group> groups = [];

  /// Saved receipts, newest first.
  final List<Receipt> receipts = [];

  /// Whether [load] has completed.
  bool loaded = false;

  Timer? _saveTimer;

  Future<File> _file() async {
    final dir = _overrideDir ?? await getApplicationDocumentsDirectory();
    final d = Directory('${dir.path}/billsplit');
    if (!d.existsSync()) d.createSync(recursive: true);
    return File('${d.path}/state.json');
  }

  /// Loads persisted state; failures leave the state empty but usable.
  Future<void> load() async {
    try {
      final f = await _file();
      if (f.existsSync()) {
        final j = jsonDecode(f.readAsStringSync()) as Map<String, dynamic>;
        people
          ..clear()
          ..addAll(
            (j['people'] as List? ?? const <dynamic>[])
                .map((e) => Person.fromJson((e as Map).cast())),
          );
        groups
          ..clear()
          ..addAll(
            (j['groups'] as List? ?? const <dynamic>[])
                .map((e) => Group.fromJson((e as Map).cast())),
          );
        receipts
          ..clear()
          ..addAll(
            (j['receipts'] as List? ?? const <dynamic>[])
                .map((e) => Receipt.fromJson((e as Map).cast())),
          );
        _prune();
      }
    } on FormatException catch (e) {
      debugPrint('State load failed (corrupt JSON): $e');
    } on FileSystemException catch (e) {
      debugPrint('State load failed (IO): $e');
    }
    loaded = true;
    notifyListeners();
  }

  /// Drop references to people that no longer exist.
  void _prune() {
    final ids = people.map((p) => p.id).toSet();
    for (final g in groups) {
      g.memberIds.removeWhere((id) => !ids.contains(id));
    }
    for (final r in receipts) {
      r.participantIds.removeWhere((id) => !ids.contains(id));
      for (final i in r.items) {
        i.assignment.customIds.removeWhere((id) => !ids.contains(id));
      }
    }
  }

  void _scheduleSave() {
    _saveTimer?.cancel();
    _saveTimer = Timer(const Duration(milliseconds: 400), save);
  }

  /// Writes the current state to disk immediately.
  Future<void> save() async {
    try {
      final f = await _file();
      f.writeAsStringSync(
        jsonEncode({
          'people': people.map((p) => p.toJson()).toList(),
          'groups': groups.map((g) => g.toJson()).toList(),
          'receipts': receipts.map((r) => r.toJson()).toList(),
        }),
      );
    } on FileSystemException catch (e) {
      debugPrint('State save failed: $e');
    }
  }

  /// Runs [fn], prunes dangling references, notifies, schedules a save.
  void mutate(void Function() fn) {
    fn();
    _prune();
    notifyListeners();
    _scheduleSave();
  }

  // Convenience CRUD -------------------------------------------------------

  /// Adds a person to the roster and returns it.
  Person addPerson(String name, {bool drinks = true}) {
    final p = Person(id: Ids.next(), name: name, drinks: drinks);
    mutate(() => people.add(p));
    return p;
  }

  /// Removes [p] everywhere (roster, groups, receipts, assignments).
  void removePerson(Person p) => mutate(() => people.remove(p));

  /// Adds an empty group and returns it.
  Group addGroup(String name) {
    final g = Group(id: Ids.next(), name: name);
    mutate(() => groups.add(g));
    return g;
  }

  /// Removes [g]; items assigned to it fall back to everyone.
  void removeGroup(Group g) => mutate(() {
        groups.remove(g);
        for (final r in receipts) {
          for (final i in r.items) {
            if (i.assignment.groupId == g.id) {
              i.assignment
                ..mode = AssignMode.everyone
                ..groupId = null;
            }
          }
        }
      });

  /// Inserts [r] at the top; empty participants default to the whole roster.
  void addReceipt(Receipt r) => mutate(() {
        if (r.participantIds.isEmpty) {
          r.participantIds.addAll(people.map((p) => p.id));
        }
        receipts.insert(0, r);
      });

  /// Deletes [r].
  void removeReceipt(Receipt r) => mutate(() => receipts.remove(r));

  @override
  void dispose() {
    _saveTimer?.cancel();
    super.dispose();
  }
}
