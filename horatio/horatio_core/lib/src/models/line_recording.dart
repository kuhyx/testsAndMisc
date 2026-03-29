import 'package:meta/meta.dart';

/// A voice recording for a specific script line.
@immutable
final class LineRecording {
  /// Creates a [LineRecording].
  const LineRecording({
    required this.id,
    required this.scriptId,
    required this.lineIndex,
    required this.filePath,
    required this.durationMs,
    required this.createdAt,
    this.grade,
  });

  /// Deserializes from a JSON map.
  factory LineRecording.fromJson(Map<String, dynamic> json) => LineRecording(
    id: json['id'] as String,
    scriptId: json['scriptId'] as String,
    lineIndex: json['lineIndex'] as int,
    filePath: json['filePath'] as String,
    durationMs: json['durationMs'] as int,
    createdAt: DateTime.parse(json['createdAt'] as String),
    grade: json['grade'] as int?,
  );

  /// Unique identifier (UUID).
  final String id;

  /// The script this recording belongs to.
  final String scriptId;

  /// Index of the line this recording is for.
  final int lineIndex;

  /// Path to the audio file on disk.
  final String filePath;

  /// Duration in milliseconds.
  final int durationMs;

  /// When this recording was created.
  final DateTime createdAt;

  /// Grade 0-5 (SM-2 quality scale), null if not yet graded.
  final int? grade;

  @override
  bool operator ==(Object other) =>
      identical(this, other) || other is LineRecording && id == other.id;

  @override
  int get hashCode => id.hashCode;

  /// Serializes to a JSON-compatible map.
  Map<String, dynamic> toJson() => {
    'id': id,
    'scriptId': scriptId,
    'lineIndex': lineIndex,
    'filePath': filePath,
    'durationMs': durationMs,
    'createdAt': createdAt.toUtc().toIso8601String(),
    'grade': grade,
  };
}
