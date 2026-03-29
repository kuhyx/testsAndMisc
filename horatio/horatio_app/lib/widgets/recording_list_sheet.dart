import 'package:flutter/material.dart';
import 'package:horatio_app/widgets/grade_stars.dart';
import 'package:horatio_core/horatio_core.dart';
import 'package:intl/intl.dart';

/// Bottom sheet listing all recordings for a line.
class RecordingListSheet extends StatelessWidget {
  /// Creates a [RecordingListSheet].
  const RecordingListSheet({
    required this.recordings,
    required this.onPlay,
    required this.onGrade,
    required this.onDelete,
    super.key,
  });

  /// Recordings to display.
  final List<LineRecording> recordings;

  /// Called when play is tapped for a recording.
  final ValueChanged<LineRecording> onPlay;

  /// Called when a grade is selected for a recording.
  final void Function(String id, int grade) onGrade;

  /// Called when delete is tapped for a recording.
  final ValueChanged<String> onDelete;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(16),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Recordings', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        if (recordings.isEmpty)
          const Center(child: Text('No recordings'))
        else
          ...recordings.map(
            (r) => ListTile(
              leading: IconButton(
                icon: const Icon(Icons.play_arrow),
                onPressed: () => onPlay(r),
              ),
              title: Text(
                '${(r.durationMs / 1000).toStringAsFixed(1)}s - '
                '${DateFormat.yMd().format(r.createdAt)}',
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  GradeStars(
                    grade: r.grade,
                    onGrade: (grade) => onGrade(r.id, grade),
                  ),
                  if (r.grade == null) const Text('Not graded'),
                ],
              ),
              trailing: IconButton(
                icon: const Icon(Icons.delete),
                onPressed: () => onDelete(r.id),
              ),
            ),
          ),
      ],
    ),
  );
}
