import 'package:horatio_core/src/models/note_category.dart';
import 'package:meta/meta.dart';

/// A free-text interpretive note attached to a whole script line.
@immutable
final class LineNote {
  /// Creates a [LineNote].
  const LineNote({
    required this.id,
    required this.lineIndex,
    required this.category,
    required this.text,
    required this.createdAt,
  });

  /// Deserializes from a JSON map.
  factory LineNote.fromJson(Map<String, dynamic> json) => LineNote(
    id: json['id'] as String,
    lineIndex: json['lineIndex'] as int,
    category: NoteCategory.values.byName(json['category'] as String),
    text: json['text'] as String,
    createdAt: DateTime.parse(json['createdAt'] as String),
  );

  /// Unique identifier (UUID).
  final String id;

  /// Index of the [ScriptLine] this note is attached to.
  final int lineIndex;

  /// The category of this note.
  final NoteCategory category;

  /// Free-text note content.
  final String text;

  /// When this note was created.
  final DateTime createdAt;

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is LineNote && id == other.id;

  @override
  int get hashCode => id.hashCode;

  /// Serializes to a JSON-compatible map.
  Map<String, dynamic> toJson() => {
    'id': id,
    'lineIndex': lineIndex,
    'category': category.name,
    'text': text,
    'createdAt': createdAt.toUtc().toIso8601String(),
  };
}
