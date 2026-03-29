import 'package:flutter/material.dart';

/// A small mic icon with count badge, showing recordings per line.
class RecordingBadge extends StatelessWidget {
  /// Creates a [RecordingBadge].
  const RecordingBadge({
    required this.recordingCount,
    required this.onTap,
    super.key,
  });

  /// Number of recordings for the line.
  final int recordingCount;

  /// Callback when tapped.
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    if (recordingCount == 0) return const SizedBox.shrink();
    return GestureDetector(
      onTap: onTap,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.mic, size: 16),
          const SizedBox(width: 2),
          Text(
            '$recordingCount',
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
