import 'package:horatio_core/src/models/line_note.dart';
import 'package:horatio_core/src/models/text_mark.dart';
import 'package:meta/meta.dart';

/// A point-in-time record of all annotations for a script.
@immutable
final class AnnotationSnapshot {
  /// Creates an [AnnotationSnapshot] with unmodifiable lists.
  AnnotationSnapshot({
    required this.id,
    required this.scriptId,
    required this.timestamp,
    required List<TextMark> marks,
    required List<LineNote> notes,
  }) : marks = List.unmodifiable(marks),
       notes = List.unmodifiable(notes);

  /// Deserializes from a JSON map.
  factory AnnotationSnapshot.fromJson(Map<String, dynamic> json) =>
      AnnotationSnapshot(
        id: json['id'] as String,
        scriptId: json['scriptId'] as String,
        timestamp: DateTime.parse(json['timestamp'] as String),
        marks: (json['marks'] as List<dynamic>)
            .map((e) => TextMark.fromJson(e as Map<String, dynamic>))
            .toList(),
        notes: (json['notes'] as List<dynamic>)
            .map((e) => LineNote.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  /// Unique identifier (UUID).
  final String id;

  /// The script these annotations belong to.
  final String scriptId;

  /// When this snapshot was taken.
  final DateTime timestamp;

  /// All text marks at snapshot time.
  final List<TextMark> marks;

  /// All line notes at snapshot time.
  final List<LineNote> notes;

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is AnnotationSnapshot && id == other.id;

  @override
  int get hashCode => id.hashCode;

  /// Serializes to a JSON-compatible map.
  Map<String, dynamic> toJson() => {
    'id': id,
    'scriptId': scriptId,
    'timestamp': timestamp.toUtc().toIso8601String(),
    'marks': marks.map((m) => m.toJson()).toList(),
    'notes': notes.map((n) => n.toJson()).toList(),
  };
}
