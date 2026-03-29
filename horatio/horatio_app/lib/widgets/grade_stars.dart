import 'package:flutter/material.dart';

/// A 0-5 grade widget with tappable stars and a "Blackout" (grade 0) button.
class GradeStars extends StatelessWidget {
  /// Creates a [GradeStars].
  const GradeStars({
    required this.grade,
    required this.onGrade,
    super.key,
  });

  /// Current grade (0-5), null if not yet graded.
  final int? grade;

  /// Called with the selected grade (0-5).
  final ValueChanged<int> onGrade;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextButton(
            onPressed: () => onGrade(0),
            style: TextButton.styleFrom(
              foregroundColor: grade == 0 ? Colors.red : null,
            ),
            child: const Text('Blackout'),
          ),
          for (var i = 1; i <= 5; i++)
            IconButton(
              icon: Icon(
                grade != null && i <= grade! ? Icons.star : Icons.star_border,
                color: Colors.amber,
              ),
              onPressed: () => onGrade(i),
            ),
        ],
      );
}
