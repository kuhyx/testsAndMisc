import 'package:flutter/material.dart';
import 'package:horatio_core/horatio_core.dart';

/// Bottom action bar for record/play controls on a selected line.
class RecordingActionBar extends StatelessWidget {
  /// Creates a [RecordingActionBar].
  const RecordingActionBar({
    required this.isRecording,
    required this.elapsed,
    required this.latestRecording,
    required this.onRecord,
    required this.onStop,
    required this.onPlay,
    super.key,
  });

  /// Whether currently recording.
  final bool isRecording;

  /// Elapsed recording time.
  final Duration elapsed;

  /// Most recent recording for the selected line (null if none).
  final LineRecording? latestRecording;

  /// Start recording callback.
  final VoidCallback onRecord;

  /// Stop recording callback.
  final VoidCallback onStop;

  /// Play last recording callback.
  final VoidCallback onPlay;

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes;
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      border: Border(
        top: BorderSide(
          color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.3),
        ),
      ),
    ),
    child: Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (isRecording) ...[
          IconButton(
            icon: const Icon(Icons.stop, color: Colors.red),
            onPressed: onStop,
            tooltip: 'Stop Recording',
          ),
          Text(_formatDuration(elapsed)),
        ] else ...[
          IconButton(
            icon: const Icon(Icons.mic),
            onPressed: onRecord,
            tooltip: 'Record',
          ),
        ],
        const SizedBox(width: 16),
        IconButton(
          icon: const Icon(Icons.play_arrow),
          onPressed: latestRecording != null ? onPlay : null,
          tooltip: 'Play Last Recording',
        ),
      ],
    ),
  );
}
