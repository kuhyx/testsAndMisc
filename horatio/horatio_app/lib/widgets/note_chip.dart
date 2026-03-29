import 'package:flutter/material.dart';
import 'package:horatio_core/horatio_core.dart';

/// Category icons for note chips.
const Map<NoteCategory, IconData> noteCategoryIcons = {
  NoteCategory.intention: Icons.psychology,
  NoteCategory.subtext: Icons.chat_bubble_outline,
  NoteCategory.blocking: Icons.directions_walk,
  NoteCategory.emotion: Icons.favorite,
  NoteCategory.delivery: Icons.record_voice_over,
  NoteCategory.general: Icons.note,
};

/// An inline chip displaying a note's category icon and truncated text.
class NoteChip extends StatelessWidget {
  /// Creates a [NoteChip].
  const NoteChip({
    required this.note,
    required this.onTap,
    required this.onDelete,
    super.key,
  });

  /// The note to display.
  final LineNote note;

  /// Called when the chip is tapped (edit).
  final VoidCallback onTap;

  /// Called when the chip is long-pressed (delete).
  final VoidCallback onDelete;

  String get _truncatedText =>
      note.text.length > 30 ? '${note.text.substring(0, 30)}...' : note.text;

  @override
  Widget build(BuildContext context) => GestureDetector(
    onLongPress: onDelete,
    child: ActionChip(
      avatar: Icon(noteCategoryIcons[note.category] ?? Icons.note, size: 16),
      label: Text(_truncatedText),
      onPressed: onTap,
    ),
  );
}
