/// Split computation. Grosz-exact: every item's shares sum to exactly the
/// item total (largest-remainder distribution, deterministic order), so the
/// per-person totals always reconcile with the receipt to the grosz.
library;

import 'package:billsplit/domain/models.dart';

/// Accumulated amounts one person owes on a receipt.
class PersonTotal {
  /// Creates an empty total for [personId].
  PersonTotal(this.personId);

  /// The person this total belongs to.
  final String personId;

  /// Everything owed, in grosze.
  int totalGr = 0;

  /// The alcohol portion of [totalGr].
  int alcoholGr = 0;

  /// The non-alcohol portion of [totalGr].
  int get restGr => totalGr - alcoholGr;
}

/// Result of [computeSplit].
class SplitResult {
  /// Bundles the computed maps.
  SplitResult({
    required this.perPerson,
    required this.itemShares,
    required this.unassigned,
  });

  /// personId → totals. Contains every receipt participant, even if 0.
  final Map<String, PersonTotal> perPerson;

  /// itemId → (personId → share in grosze). Only resolved participants.
  final Map<String, Map<String, int>> itemShares;

  /// Items that resolved to zero participants (excluded from totals).
  final List<Item> unassigned;

  /// Sum of all per-person totals, in grosze.
  int get assignedTotalGr => perPerson.values.fold(0, (s, p) => s + p.totalGr);
}

/// People from [Receipt.participantIds] that still exist in [roster].
List<Person> receiptParticipants(Receipt receipt, List<Person> roster) =>
    roster.where((p) => receipt.participantIds.contains(p.id)).toList();

/// Resolves an item's assignment to concrete people, always intersected with
/// the receipt's participant pool.
List<Person> resolveParticipants(
  Item item,
  Receipt receipt,
  List<Person> roster,
  List<Group> groups,
) {
  final pool = receiptParticipants(receipt, roster);
  final a = item.assignment;
  switch (a.mode) {
    case AssignMode.everyone:
      return pool;
    case AssignMode.drinkers:
      return pool.where((p) => p.drinks).toList();
    case AssignMode.nonDrinkers:
      return pool.where((p) => !p.drinks).toList();
    case AssignMode.group:
      final g = groups.where((g) => g.id == a.groupId).firstOrNull;
      if (g == null) return const [];
      return pool.where((p) => g.memberIds.contains(p.id)).toList();
    case AssignMode.custom:
      return pool.where((p) => a.customIds.contains(p.id)).toList();
  }
}

/// Splits [totalGr] between [personIds]. Base share is floor(total/n); the
/// remainder is handed out one grosz at a time starting at a position derived
/// from [rotation] (e.g. a stable hash of the item id). Rotating the start
/// per item avoids systematically overcharging the same person across a whole
/// receipt, while staying fully deterministic. Shares always sum to exactly
/// [totalGr] (also for negative totals, e.g. returns).
Map<String, int> splitAmount(
  int totalGr,
  List<String> personIds, {
  int rotation = 0,
}) {
  if (personIds.isEmpty) return const {};
  final ids = [...personIds]..sort();
  final n = ids.length;
  final base = (totalGr / n).floor();
  final remainder = totalGr - base * n; // 0 <= remainder < n, also if negative
  final start = ((rotation % n) + n) % n;
  final out = <String, int>{for (final id in ids) id: base};
  for (var k = 0; k < remainder; k++) {
    out[ids[(start + k) % n]] = base + 1;
  }
  return out;
}

/// Stable string hash (unlike `String.hashCode`, which is not guaranteed
/// identical across Dart VM runs) so splits don't shift between app launches.
int stableHash(String s) {
  var h = 0;
  for (final c in s.codeUnits) {
    h = (h * 31 + c) & 0x7fffffff;
  }
  return h;
}

/// Computes the full split of [receipt] between [roster] members using
/// [groups] for group-mode assignments.
SplitResult computeSplit(
  Receipt receipt,
  List<Person> roster,
  List<Group> groups,
) {
  final perPerson = <String, PersonTotal>{
    for (final p in receiptParticipants(receipt, roster))
      p.id: PersonTotal(p.id),
  };
  final itemShares = <String, Map<String, int>>{};
  final unassigned = <Item>[];

  for (final item in receipt.items) {
    final people = resolveParticipants(item, receipt, roster, groups);
    if (people.isEmpty) {
      unassigned.add(item);
      continue;
    }
    final shares = splitAmount(
      item.totalGr,
      people.map((p) => p.id).toList(),
      rotation: stableHash(item.id),
    );
    itemShares[item.id] = shares;
    final isAlcohol = item.category == Categories.alcohol;
    shares.forEach((pid, amount) {
      perPerson[pid]!
        ..totalGr += amount
        ..alcoholGr += isAlcohol ? amount : 0;
    });
  }

  return SplitResult(
    perPerson: perPerson,
    itemShares: itemShares,
    unassigned: unassigned,
  );
}

extension<T> on Iterable<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
