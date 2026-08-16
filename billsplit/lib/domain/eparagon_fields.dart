/// Field extraction helpers for the e-paragon parser.
///
/// Split out of eparagon_parser.dart to keep it under the 250-line cap.
/// A `part` because Dart privates are library-scoped.

part of 'eparagon_parser.dart';

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
