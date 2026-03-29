import 'package:flutter/material.dart';
import 'package:horatio_core/horatio_core.dart';

/// Displays a word-level diff with color-coded highlights.
class LineDiffWidget extends StatelessWidget {
  /// Creates a [LineDiffWidget].
  const LineDiffWidget({
    required this.segments,
    super.key,
  });

  /// The diff segments to display.
  final List<DiffSegment> segments;

  @override
  Widget build(BuildContext context) => RichText(
        text: TextSpan(
          style: Theme.of(context).textTheme.bodyLarge,
          children: segments.map(_buildSpan).toList(),
        ),
      );

  TextSpan _buildSpan(DiffSegment segment) {
    final (Color? bg, TextDecoration? decoration) = switch (segment.type) {
      DiffType.match => (null, null),
      DiffType.extra => (Colors.red.withValues(alpha: 0.3), TextDecoration.lineThrough),
      DiffType.missing => (Colors.green.withValues(alpha: 0.3), TextDecoration.underline),
    };

    return TextSpan(
      text: '${segment.text} ',
      style: TextStyle(
        backgroundColor: bg,
        decoration: decoration,
      ),
    );
  }
}
