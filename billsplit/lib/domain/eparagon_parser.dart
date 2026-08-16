/// Parser for Polish fiscal e-receipts (e-paragon / JPK_KASA_PARAGON_v2-0),
/// e.g. the JSON files produced by the Biedronka app.
///
/// Accepted inputs:
///  * the full wrapper JSON containing a `data` field with a JWS
///    (header.payload.signature, base64url) whose payload is the JPK document;
///  * the decoded JPK payload itself (an object with `dokument.paragon`);
///  * a bare JWS token string.
///
/// The signature is NOT verified — this app only reads the contents.
library;

import 'dart:convert';

import 'package:billsplit/domain/models.dart';

part 'eparagon_fields.dart';

/// A parsed receipt plus non-fatal [warnings] collected on the way.
class EParagonResult {
  /// Bundles a parsed [receipt] with its [warnings].
  EParagonResult({required this.receipt, required this.warnings});

  /// The parsed receipt.
  final Receipt receipt;

  /// Human-readable warnings (e.g. sum mismatches, skipped lines).
  final List<String> warnings;
}

/// Thrown when the input cannot be interpreted as an e-paragon.
class EParagonParseException implements Exception {
  /// Creates the exception with a user-facing [message].
  EParagonParseException(this.message);

  /// User-facing description of what went wrong.
  final String message;

  @override
  String toString() => 'EParagonParseException: $message';
}

const _alcoholKeywords = [
  'wódk',
  'wodka',
  'vodka',
  'piwo',
  'wino',
  'whisk',
  'likier',
  'nalewk',
  'cydr',
  ' rum',
  'gin ',
  'tequil',
  'brandy',
  'koniak',
  'bourbon',
];

const _mixerKeywords = [
  'tonic',
  'tonik',
  'kinley',
  'citrus mix',
  'limonka',
  'cytryna',
];

/// Parses [source] and returns just the receipt; see [parseEParagonDetailed].
Receipt parseEParagon(String source) => parseEParagonDetailed(source).receipt;

/// Parses [source] (wrapper JSON, bare JPK payload, or bare JWS) into a
/// [Receipt] plus warnings. Throws [EParagonParseException] on unusable input.
EParagonResult parseEParagonDetailed(String source) {
  final warnings = <String>[];
  final payload = _extractPayload(source);

  final dokument = payload['dokument'];
  if (dokument is! Map) {
    throw EParagonParseException('No "dokument" object in payload.');
  }
  final paragon = dokument['paragon'];
  if (paragon is! Map) {
    throw EParagonParseException('No "dokument.paragon" object in payload.');
  }

  final store = _storeName(dokument);
  final date = _saleDate(paragon, dokument);

  final items = <Item>[];
  final pozycje = paragon['pozycja'];
  if (pozycje is List) {
    for (final p in pozycje) {
      final towar = (p is Map) ? p['towar'] : null;
      if (towar is! Map) continue;
      final it = _itemFromTowar(towar.cast<String, dynamic>(), warnings);
      if (it != null) items.add(it);
    }
  }
  if (items.isEmpty) {
    throw EParagonParseException('Receipt has no line items.');
  }

  // Bottle deposits ("opakowania zwrotne" / kaucja) are outside sumaBrutto but
  // part of what was paid; add each as a regular splittable line.
  final opak = paragon['opak'];
  if (opak is Map) {
    final dane = opak['daneOpak'];
    if (dane is List) {
      for (final d in dane) {
        if (d is! Map) continue;
        final cena = _asInt(d['cena']);
        final iloscMil = _asInt(d['ilosc']); // thousandths
        final qty = iloscMil / 1000;
        final total = (cena * iloscMil / 1000).round();
        if (total == 0) continue;
        items.add(
          Item(
            id: Ids.next(),
            name: 'Kaucja: '
                '${(d['nazwa'] as String? ?? 'opakowanie').trim()} (deposit)',
            totalGr: total,
            qty: qty,
            unitPriceGr: cena,
            category: Categories.deposit,
          ),
        );
      }
    }
  }

  // Reconciliation figures.
  var paid = _asIntOrNull((paragon['total'] as Map?)?['zaplZwrot']);
  final sumaBrutto = _asIntOrNull((paragon['podsum'] as Map?)?['sumaBrutto']);
  final opakWart = _asIntOrNull((paragon['opak'] as Map?)?['wart']) ?? 0;
  paid ??= sumaBrutto == null ? null : sumaBrutto + opakWart;

  if (sumaBrutto != null) {
    final goods = items
        .where((i) => i.category != Categories.deposit)
        .fold(0, (s, i) => s + i.totalGr);
    if (goods != sumaBrutto) {
      warnings.add(
        'Sum of parsed items (${formatPln(goods)}) differs from receipt '
        'sumaBrutto (${formatPln(sumaBrutto)}).',
      );
    }
  }

  final title = [
    if (store != null) store,
    _iso(date),
  ].join(' ');

  return EParagonResult(
    receipt: Receipt(
      id: Ids.next(),
      title: title,
      store: store,
      date: date,
      items: items,
      paidTotalGr: paid,
    ),
    warnings: warnings,
  );
}

String? _storeName(Map<dynamic, dynamic> dokument) {
  final podmiot = dokument['podmiot1'];
  if (podmiot is! Map) return null;
  final name = (podmiot['nazwaPod'] as String?)?.trim();
  if (name == null || name.isEmpty) return null;
  // Friendlier alias for the most common chain.
  if (name.toUpperCase().contains('JERONIMO MARTINS')) return 'Biedronka';
  return name;
}
