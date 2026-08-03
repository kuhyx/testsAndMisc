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

DateTime _saleDate(
  Map<dynamic, dynamic> paragon,
  Map<dynamic, dynamic> dokument,
) {
  final raw =
      paragon['zakSprzed'] ?? (dokument['naglowek'] as Map?)?['dataJPK'];
  if (raw is String) {
    final d = DateTime.tryParse(raw);
    if (d != null) return d.toLocal();
  }
  return DateTime.now();
}

String _iso(DateTime d) {
  final m = d.month.toString().padLeft(2, '0');
  final day = d.day.toString().padLeft(2, '0');
  return '${d.year}-$m-$day';
}

Map<String, dynamic> _extractPayload(String source) {
  dynamic root;
  try {
    root = jsonDecode(source.trim());
  } on FormatException {
    // Maybe the user pasted just the JWS token.
    final p = _tryJws(source.trim());
    if (p != null) return p;
    throw EParagonParseException(
      'Input is neither valid JSON nor a JWS.',
    );
  }
  if (root is Map) {
    if (root['dokument'] is Map) return root.cast<String, dynamic>();
    final data = root['data'];
    if (data is String) {
      final p = _tryJws(data);
      if (p != null) return p;
      throw EParagonParseException('"data" field is not a decodable JWS.');
    }
  }
  throw EParagonParseException(
    'Unrecognized structure: expected e-paragon wrapper or JPK payload.',
  );
}

Map<String, dynamic>? _tryJws(String token) {
  final parts = token.split('.');
  if (parts.length != 3) return null;
  try {
    final normalized = base64Url.normalize(parts[1]);
    final decoded = utf8.decode(base64Url.decode(normalized));
    final obj = jsonDecode(decoded);
    return obj is Map ? obj.cast<String, dynamic>() : null;
  } on FormatException {
    return null;
  }
}

Item? _itemFromTowar(Map<String, dynamic> t, List<String> warnings) {
  var name = (t['nazwa'] as String? ?? '').trim();
  // Names end with the VAT rate letter, e.g. "Tonic                    A".
  if (name.length > 2 &&
      name[name.length - 2] == ' ' &&
      RegExp(r'[A-G]$').hasMatch(name)) {
    name = name.substring(0, name.length - 2).trim();
  }
  name = name.replaceAll(RegExp(r'\s+'), ' ');
  if (name.isEmpty) return null;

  final total = _asIntOrNull(t['brutto']);
  if (total == null) {
    warnings.add('Skipped "$name": missing brutto amount.');
    return null;
  }
  final unit = _asIntOrNull(t['cena']) ?? 0;
  final qty = _parseQty(t['ilosc']);
  final rabat = t['rabat'];
  final discount = rabat is Map ? (_asIntOrNull(rabat['wart']) ?? 0) : 0;

  final lower = name.toLowerCase();
  var category = Categories.general;
  var assignment = Assignment();
  if (_alcoholKeywords.any(lower.contains)) {
    category = Categories.alcohol;
    assignment = Assignment(mode: AssignMode.drinkers);
  } else if (_mixerKeywords.any(lower.contains)) {
    category = Categories.mixer; // still split among everyone by default
  }

  return Item(
    id: Ids.next(),
    name: name,
    totalGr: total,
    qty: qty,
    unitPriceGr: unit,
    discountGr: discount,
    category: category,
    assignment: assignment,
  );
}

double _parseQty(dynamic v) {
  if (v is num) return v.toDouble();
  if (v is String) {
    return double.tryParse(v.replaceAll(',', '.').trim()) ?? 1;
  }
  return 1;
}

int _asInt(dynamic v) => _asIntOrNull(v) ?? 0;

int? _asIntOrNull(dynamic v) {
  if (v is int) return v;
  if (v is num) return v.round();
  if (v is String) return int.tryParse(v);
  return null;
}
