/// Domain models. All money values are ints in grosze (1/100 PLN) to avoid
/// floating point drift; formatting happens only at the UI/export edge.
library;

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

/// The assignment of one item: a symbolic mode plus mode-specific data.
class Assignment {
  /// Creates an assignment; defaults to [AssignMode.everyone].
  Assignment({
    this.mode = AssignMode.everyone,
    this.groupId,
    Set<String>? customIds,
  }) : customIds = customIds ?? <String>{};

  /// Restores an assignment from its [toJson] map.
  factory Assignment.fromJson(Map<String, dynamic> j) => Assignment(
        mode: AssignMode.values.asNameMap()[j['mode']] ?? AssignMode.everyone,
        groupId: j['groupId'] as String?,
        customIds: (j['customIds'] as List? ?? const <dynamic>[])
            .cast<String>()
            .toSet(),
      );

  /// Current mode.
  AssignMode mode;

  /// Group id when [mode] is [AssignMode.group].
  String? groupId;

  /// Hand-picked person ids when [mode] is [AssignMode.custom].
  final Set<String> customIds;

  /// JSON representation for persistence.
  Map<String, dynamic> toJson() => {
        'mode': mode.name,
        if (groupId != null) 'groupId': groupId,
        'customIds': customIds.toList(),
      };
}

/// Standard item categories. [Item.category] is free text so users can add
/// their own; these constants are the ones the importer produces.
abstract final class Categories {
  /// Alcoholic drinks — default to drinkers only.
  static const alcohol = 'Alcohol';

  /// Mixers (tonic, limes, …) — tagged for visibility, split among everyone.
  static const mixer = 'Mixer';

  /// Returnable bottle deposits (kaucja).
  static const deposit = 'Deposit';

  /// Anything else.
  static const general = 'General';
}

/// One receipt line.
class Item {
  /// Creates an item; [totalGr] is the post-discount line total.
  Item({
    required this.id,
    required this.name,
    required this.totalGr,
    this.qty = 1,
    this.unitPriceGr = 0,
    this.discountGr = 0,
    this.category = Categories.general,
    Assignment? assignment,
  }) : assignment = assignment ?? Assignment();

  /// Restores an item from its [toJson] map.
  factory Item.fromJson(Map<String, dynamic> j) => Item(
        id: j['id'] as String,
        name: j['name'] as String,
        totalGr: j['totalGr'] as int,
        qty: (j['qty'] as num? ?? 1).toDouble(),
        unitPriceGr: j['unitPriceGr'] as int? ?? 0,
        discountGr: j['discountGr'] as int? ?? 0,
        category: j['category'] as String? ?? Categories.general,
        assignment: Assignment.fromJson(
          (j['assignment'] as Map?)?.cast<String, dynamic>() ?? const {},
        ),
      );

  /// Stable unique id.
  final String id;

  /// Display name.
  String name;

  /// Final line total after discount — the ground truth used for splitting.
  int totalGr;

  /// Quantity (may be fractional for weighed goods).
  double qty;

  /// Unit price in grosze.
  int unitPriceGr;

  /// Discount already included in [totalGr]; kept for display (<= 0).
  int discountGr;

  /// Free-text category; see [Categories] for the standard values.
  String category;

  /// Who shares this item.
  Assignment assignment;

  /// JSON representation for persistence.
  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'totalGr': totalGr,
        'qty': qty,
        'unitPriceGr': unitPriceGr,
        'discountGr': discountGr,
        'category': category,
        'assignment': assignment.toJson(),
      };
}

/// One shopping receipt with its items and participants.
class Receipt {
  /// Creates a receipt; [participantIds] defaults to empty.
  Receipt({
    required this.id,
    required this.title,
    this.store,
    DateTime? date,
    List<Item>? items,
    Set<String>? participantIds,
    this.paidTotalGr,
  })  : date = date ?? DateTime.now(),
        items = items ?? <Item>[],
        participantIds = participantIds ?? <String>{};

  /// Restores a receipt from its [toJson] map.
  factory Receipt.fromJson(Map<String, dynamic> j) => Receipt(
        id: j['id'] as String,
        title: j['title'] as String,
        store: j['store'] as String?,
        date: DateTime.tryParse(j['date'] as String? ?? '') ?? DateTime.now(),
        items: (j['items'] as List? ?? const <dynamic>[])
            .map((e) => Item.fromJson((e as Map).cast<String, dynamic>()))
            .toList(),
        participantIds: (j['participantIds'] as List? ?? const <dynamic>[])
            .cast<String>()
            .toSet(),
        paidTotalGr: j['paidTotalGr'] as int?,
      );

  /// Stable unique id.
  final String id;

  /// Display title.
  String title;

  /// Store name, if known.
  String? store;

  /// Sale date.
  DateTime date;

  /// Line items.
  final List<Item> items;

  /// Subset of the roster taking part in this receipt.
  final Set<String> participantIds;

  /// What was actually paid (incl. deposits) — used for the reconciliation
  /// check. Null for manual receipts where the user never entered it.
  int? paidTotalGr;

  /// Sum of all item totals in grosze.
  int get itemsTotalGr => items.fold(0, (s, i) => s + i.totalGr);

  /// JSON representation for persistence.
  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'store': store,
        'date': date.toIso8601String(),
        'items': items.map((i) => i.toJson()).toList(),
        'participantIds': participantIds.toList(),
        'paidTotalGr': paidTotalGr,
      };
}

/// Simple unique id source: time + counter. Good enough for a local,
/// single-user app.
class Ids {
  static int _c = 0;

  /// Returns a new unique id.
  static String next() =>
      '${DateTime.now().microsecondsSinceEpoch.toRadixString(36)}'
      '-${(_c++).toRadixString(36)}';
}
