import 'package:horatio_core/src/models/mark_type.dart';
import 'package:meta/meta.dart';

/// A span-based delivery mark on text within a script line.
@immutable
final class TextMark {
  /// Creates a [TextMark] with validated offsets.
  const TextMark({
    required this.id,
    required this.lineIndex,
    required this.startOffset,
    required this.endOffset,
    required this.type,
    required this.createdAt,
  }) : assert(startOffset >= 0, 'startOffset must be non-negative'),
       assert(
         endOffset > startOffset,
         'endOffset must be greater than startOffset',
       );

  /// Deserializes from a JSON map.
  ///
  /// Throws [ArgumentError] if [type] is not a valid [MarkType] name.
  factory TextMark.fromJson(Map<String, dynamic> json) => TextMark(
    id: json['id'] as String,
    lineIndex: json['lineIndex'] as int,
    startOffset: json['startOffset'] as int,
    endOffset: json['endOffset'] as int,
    type: MarkType.values.byName(json['type'] as String),
    createdAt: DateTime.parse(json['createdAt'] as String),
  );

  /// Unique identifier (UUID).
  final String id;

  /// Index of the [ScriptLine] this mark applies to.
  final int lineIndex;

  /// Start character offset in the line text (inclusive).
  final int startOffset;

  /// End character offset in the line text (exclusive).
  final int endOffset;

  /// The type of delivery mark.
  final MarkType type;

  /// When this mark was created.
  final DateTime createdAt;

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is TextMark && id == other.id;

  @override
  int get hashCode => id.hashCode;

  /// Serializes to a JSON-compatible map.
  Map<String, dynamic> toJson() => {
    'id': id,
    'lineIndex': lineIndex,
    'startOffset': startOffset,
    'endOffset': endOffset,
    'type': type.name,
    'createdAt': createdAt.toUtc().toIso8601String(),
  };
}
