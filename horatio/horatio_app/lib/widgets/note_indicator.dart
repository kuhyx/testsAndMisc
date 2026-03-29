import 'package:flutter/material.dart';

/// A small tappable badge showing the note count for a script line.
class NoteIndicator extends StatelessWidget {
  /// Creates a [NoteIndicator].
  const NoteIndicator({
    required this.noteCount,
    required this.onTap,
    super.key,
  });

  /// Number of notes on the line.
  final int noteCount;

  /// Callback when tapped.
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    if (noteCount == 0) {
      return const SizedBox.shrink();
    }
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.primaryContainer,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          '$noteCount',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: Theme.of(context).colorScheme.onPrimaryContainer,
          ),
        ),
      ),
    );
  }
}
