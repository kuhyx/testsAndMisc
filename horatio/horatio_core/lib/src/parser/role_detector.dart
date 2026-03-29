import 'package:horatio_core/src/models/models.dart';

/// Detects patterns that indicate a character role is speaking.
///
/// Supports multiple common script formats:
/// 1. ALL CAPS name on its own line (screenplay format)
/// 2. `CHARACTER: dialogue` (colon format)
/// 3. `CHARACTER (direction) dialogue` (parenthetical)
/// 4. `[CHARACTER] dialogue` (bracketed)
final class RoleDetector {
  /// Creates a [RoleDetector].
  const RoleDetector();

  /// Character name pattern: uppercase letters, spaces, dots, hyphens.
  static const _nameChars = r"A-Z .\-'";

  /// Patterns for detecting character names, ordered by priority.
  /// Groups: (1) name, (2) dialogue.
  static final List<RegExp> _patterns = [
    // Colon format: "CHARACTER: dialogue" or "CHARACTER NAME: dialogue"
    RegExp('^([A-Z][$_nameChars]{1,40}):\\s*(.*)\$'),
    // Bracketed: "[CHARACTER] dialogue"
    RegExp('^\\[([A-Z][$_nameChars]{1,40})\\]\\s*(.*)\$'),
    // ALL CAPS standalone (screenplay format)
    RegExp('^([A-Z][$_nameChars]{1,40})\\s*\$'),
  ];

  /// Parenthetical format: "CHARACTER (direction) dialogue".
  /// Groups: (1) name, (2) direction, (3) dialogue.
  static final RegExp _parentheticalPattern = RegExp(
    '^([A-Z][$_nameChars]{1,40})\\s*\\(([^)]*)\\)\\s*(.*)\$',
  );

  /// Words that are NOT character names even if in ALL CAPS.
  static const Set<String> _excludedWords = {
    'ACT',
    'SCENE',
    'PROLOGUE',
    'EPILOGUE',
    'INTERMISSION',
    'CURTAIN',
    'FADE IN',
    'FADE OUT',
    'CUT TO',
    'END',
    'THE END',
    'CONTINUED',
    'CONT',
    'EXT',
    'INT',
  };

  /// Stage direction pattern: text in parentheses.
  static final RegExp _stageDirectionPattern = RegExp(r'\(([^)]+)\)');

  /// Attempts to parse a line as a character speaking.
  ///
  /// Returns a record of role, dialogue, and optional direction if a
  /// role is detected, or `null` if the line is not dialogue.
  ({Role role, String dialogue, StageDirection? direction})? detectRole(
    String line,
  ) {
    final trimmed = line.trim();
    if (trimmed.isEmpty) return null;

    // Try parenthetical format first (has 3 groups: name, direction, dialogue).
    final parentheticalResult = _tryParenthetical(trimmed);
    if (parentheticalResult != null) return parentheticalResult;

    // Try standard patterns (2 groups: name, dialogue).
    for (final pattern in _patterns) {
      final match = pattern.firstMatch(trimmed);
      if (match == null) continue;

      final rawName = match.group(1)!.trim();

      // Skip known non-character words.
      if (_excludedWords.contains(rawName.toUpperCase())) continue;

      // Skip very short names (likely initials or noise).
      if (rawName.length < 2) continue;

      final role = Role(name: _normalizeName(rawName));

      // Extract dialogue: group 2 if present, otherwise empty.
      final dialogue = match.groupCount >= 2
          ? (match.group(2) ?? '').trim()
          : '';

      // Extract stage direction from dialogue text.
      final directionMatch = _stageDirectionPattern.firstMatch(dialogue);
      final direction = directionMatch != null
          ? StageDirection(text: directionMatch.group(1)!)
          : null;

      // Remove stage direction from dialogue.
      final cleanDialogue = dialogue
          .replaceAll(_stageDirectionPattern, '')
          .trim();

      return (role: role, dialogue: cleanDialogue, direction: direction);
    }

    return null;
  }

  /// Tries to match the parenthetical format: CHARACTER (direction) dialogue.
  ({Role role, String dialogue, StageDirection? direction})? _tryParenthetical(
    String trimmed,
  ) {
    final match = _parentheticalPattern.firstMatch(trimmed);
    if (match == null) return null;

    final rawName = match.group(1)!.trim();
    if (_excludedWords.contains(rawName.toUpperCase())) return null;
    if (rawName.length < 2) return null;

    final role = Role(name: _normalizeName(rawName));
    final directionText = match.group(2)!.trim();
    final dialogue = (match.group(3) ?? '').trim();

    return (
      role: role,
      dialogue: dialogue,
      direction: directionText.isEmpty
          ? null
          : StageDirection(text: directionText),
    );
  }

  /// Detects whether a line is a pure stage direction.
  StageDirection? detectStageDirection(String line) {
    final trimmed = line.trim();
    // Lines entirely in parentheses or square brackets.
    if ((trimmed.startsWith('(') && trimmed.endsWith(')')) ||
        (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      return StageDirection(text: trimmed.substring(1, trimmed.length - 1));
    }
    return null;
  }

  /// Normalizes a character name to title case.
  static String _normalizeName(String raw) {
    final lower = raw.toLowerCase().split(RegExp(r'\s+'));
    return lower
        .map(
          (word) => word.isEmpty
              ? word
              : '${word[0].toUpperCase()}${word.substring(1)}',
        )
        .join(' ');
  }
}
