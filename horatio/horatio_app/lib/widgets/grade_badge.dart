import 'package:flutter/material.dart';
import 'package:horatio_core/horatio_core.dart';

/// A visual grade badge for line matching feedback.
class GradeBadge extends StatelessWidget {
  /// Creates a [GradeBadge].
  const GradeBadge({required this.grade, super.key});

  /// The match grade to display.
  final LineMatchGrade grade;

  @override
  Widget build(BuildContext context) {
    final (String label, Color color, IconData icon) = switch (grade) {
      LineMatchGrade.exact => ('Perfect!', Colors.green, Icons.check_circle),
      LineMatchGrade.minor => ('Close', Colors.orange, Icons.info_outline),
      LineMatchGrade.major => ('Needs Work', Colors.deepOrange, Icons.warning),
      LineMatchGrade.missed => ('Missed', Colors.red, Icons.cancel),
    };

    return Chip(
      avatar: Icon(icon, color: color, size: 20),
      label: Text(label),
      backgroundColor: color.withValues(alpha: 0.15),
      side: BorderSide(color: color),
    );
  }
}
