/// Domain models. All money values are ints in grosze (1/100 PLN) to avoid
/// floating point drift; formatting happens only at the UI/export edge.
library;

part 'assignment.dart';

/// Formats [grosze] as a Polish złoty string, e.g. `1234` → `12,34 zł`.
String formatPln(int grosze) {
  final neg = grosze < 0;
  final a = grosze.abs();
  final zl = a ~/ 100;
  final gr = (a % 100).toString().padLeft(2, '0');
  return '${neg ? '-' : ''}$zl,$gr zł';
}

/// A person on the shared roster.
class Person {
  /// Creates a person; [drinks] controls alcohol-item defaults.
  Person({required this.id, required this.name, this.drinks = true});

  /// Restores a person from its [toJson] map.
  factory Person.fromJson(Map<String, dynamic> j) => Person(
        id: j['id'] as String,
        name: j['name'] as String,
        drinks: j['drinks'] as bool? ?? true,
      );

  /// Stable unique id.
  final String id;

  /// Display name.
  String name;

  /// Whether this person shares alcohol items by default.
  bool drinks;

  /// JSON representation for persistence.
  Map<String, dynamic> toJson() => {'id': id, 'name': name, 'drinks': drinks};
}

/// A user-defined tag over roster members, e.g. "meat eaters".
class Group {
  /// Creates a group with optional initial [memberIds].
  Group({required this.id, required this.name, Set<String>? memberIds})
      : memberIds = memberIds ?? <String>{};

  /// Restores a group from its [toJson] map.
  factory Group.fromJson(Map<String, dynamic> j) => Group(
        id: j['id'] as String,
        name: j['name'] as String,
        memberIds: (j['memberIds'] as List? ?? const <dynamic>[])
            .cast<String>()
            .toSet(),
      );

  /// Stable unique id.
  final String id;

  /// Display name.
  String name;

  /// Ids of [Person]s belonging to this group.
  final Set<String> memberIds;

  /// JSON representation for persistence.
  Map<String, dynamic> toJson() =>
      {'id': id, 'name': name, 'memberIds': memberIds.toList()};
}

/// How an item is assigned to people.
enum AssignMode {
  /// Everyone on the receipt shares the item.
  everyone,

  /// Only participants with [Person.drinks] set share the item.
  drinkers,

  /// Only participants without [Person.drinks] share the item.
  nonDrinkers,

  /// Members of one [Group] share the item.
  group,

  /// An explicit hand-picked set of people shares the item.
  custom,
}
