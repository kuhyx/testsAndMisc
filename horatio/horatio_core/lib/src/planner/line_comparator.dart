import 'dart:math' as math;

/// Compares the actor's input against the expected line.
final class LineComparator {
  /// Creates a [LineComparator].
  const LineComparator();

  /// Calculates Levenshtein edit distance between two strings.
  int levenshteinDistance(String a, String b) {
    if (a == b) return 0;
    if (a.isEmpty) return b.length;
    if (b.isEmpty) return a.length;

    // Use two rows for space efficiency.
    var previousRow = List<int>.generate(b.length + 1, (i) => i);
    var currentRow = List<int>.filled(b.length + 1, 0);

    for (var i = 1; i <= a.length; i++) {
      currentRow[0] = i;
      for (var j = 1; j <= b.length; j++) {
        final cost = a[i - 1] == b[j - 1] ? 0 : 1;
        currentRow[j] = math.min(
          math.min(
            currentRow[j - 1] + 1, // insertion
            previousRow[j] + 1, // deletion
          ),
          previousRow[j - 1] + cost, // substitution
        );
      }
      final temp = previousRow;
      previousRow = currentRow;
      currentRow = temp;
    }

    return previousRow[b.length];
  }

  /// Returns a similarity score between 0.0 (completely different)
  /// and 1.0 (identical), based on normalized Levenshtein distance.
  double similarity(String expected, String actual) {
    final normalizedExpected = _normalize(expected);
    final normalizedActual = _normalize(actual);

    if (normalizedExpected.isEmpty && normalizedActual.isEmpty) return 1;

    final maxLen = math.max(normalizedExpected.length, normalizedActual.length);
    if (maxLen == 0) return 1;

    final distance = levenshteinDistance(normalizedExpected, normalizedActual);
    return 1.0 - (distance / maxLen);
  }

  /// Grades the actor's response.
  LineMatchGrade grade(String expected, String actual) {
    final score = similarity(expected, actual);
    if (score >= 0.95) return LineMatchGrade.exact;
    if (score >= 0.80) return LineMatchGrade.minor;
    if (score >= 0.50) return LineMatchGrade.major;
    return LineMatchGrade.missed;
  }

  /// Produces a word-level diff between [expected] and [actual].
  ///
  /// Returns a list of [DiffSegment]s indicating matching, extra,
  /// or missing words.
  List<DiffSegment> wordDiff(String expected, String actual) {
    final expectedWords = _normalize(expected).split(RegExp(r'\s+'));
    final actualWords = _normalize(actual).split(RegExp(r'\s+'));
    final segments = <DiffSegment>[];

    var ei = 0;
    var ai = 0;

    while (ei < expectedWords.length && ai < actualWords.length) {
      if (expectedWords[ei] == actualWords[ai]) {
        segments.add(
          DiffSegment(text: expectedWords[ei], type: DiffType.match),
        );
        ei++;
        ai++;
      } else {
        // Simple greedy: mark expected word as missing, actual as extra.
        segments
          ..add(DiffSegment(text: expectedWords[ei], type: DiffType.missing))
          ..add(DiffSegment(text: actualWords[ai], type: DiffType.extra));
        ei++;
        ai++;
      }
    }

    // Remaining expected words are missing.
    while (ei < expectedWords.length) {
      segments.add(
        DiffSegment(text: expectedWords[ei], type: DiffType.missing),
      );
      ei++;
    }

    // Remaining actual words are extra.
    while (ai < actualWords.length) {
      segments.add(DiffSegment(text: actualWords[ai], type: DiffType.extra));
      ai++;
    }

    return segments;
  }

  /// Normalizes text for comparison: lowercase, collapse whitespace.
  static String _normalize(String text) =>
      text.toLowerCase().replaceAll(RegExp(r'\s+'), ' ').trim();
}

/// Grade of how well the actor's line matched the expected text.
enum LineMatchGrade {
  /// 95%+ similarity — essentially correct.
  exact,

  /// 80–95% similarity — minor deviations.
  minor,

  /// 50–80% similarity — major deviations.
  major,

  /// Below 50% — effectively missed.
  missed,
}

/// A segment in a word-level diff.
final class DiffSegment {
  /// Creates a [DiffSegment].
  const DiffSegment({required this.text, required this.type});

  /// The word or phrase.
  final String text;

  /// Whether this segment matches, is extra, or is missing.
  final DiffType type;

  @override
  String toString() => 'Diff(${type.name}: $text)';
}

/// Type of diff segment.
enum DiffType {
  /// Word matches between expected and actual.
  match,

  /// Word present in actual but not expected.
  extra,

  /// Word present in expected but not actual.
  missing,
}
