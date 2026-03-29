import 'dart:math';

import 'package:flutter/material.dart';
import 'package:horatio_core/horatio_core.dart';

/// Color map for each [MarkType].
const Map<MarkType, Color> markColors = {
  MarkType.stress: Color.fromRGBO(244, 67, 54, 0.3),
  MarkType.pause: Color.fromRGBO(33, 150, 243, 0.3),
  MarkType.breath: Color.fromRGBO(76, 175, 80, 0.3),
  MarkType.emphasis: Color.fromRGBO(255, 152, 0, 0.3),
  MarkType.slowDown: Color.fromRGBO(156, 39, 176, 0.3),
  MarkType.speedUp: Color.fromRGBO(0, 150, 136, 0.3),
};

/// Renders text with colored highlight spans for [TextMark] overlays.
class MarkOverlay extends StatelessWidget {
  /// Creates a [MarkOverlay].
  const MarkOverlay({
    required this.text,
    required this.marks,
    this.style,
    super.key,
  });

  /// The full line text.
  final String text;

  /// Marks to overlay on the text.
  final List<TextMark> marks;

  /// Base text style.
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    final defaultStyle =
        style ?? DefaultTextStyle.of(context).style;
    if (marks.isEmpty) {
      return RichText(text: TextSpan(text: text, style: defaultStyle));
    }
    return RichText(
      text: TextSpan(style: defaultStyle, children: _buildSpans()),
    );
  }

  List<TextSpan> _buildSpans() {
    // Collect boundary events, clamped to valid text range.
    final length = text.length;
    final events = <({int offset, bool isStart, MarkType type})>[];
    for (final mark in marks) {
      final start = mark.startOffset.clamp(0, length);
      final end = mark.endOffset.clamp(0, length);
      if (start >= end) continue;
      events
        ..add((offset: start, isStart: true, type: mark.type))
        ..add((offset: end, isStart: false, type: mark.type));
    }
    events.sort((a, b) => a.offset.compareTo(b.offset));

    final spans = <TextSpan>[];
    var cursor = 0;
    final activeTypes = <MarkType>[];

    for (final event in events) {
      final pos = min(event.offset, length);
      if (pos > cursor) {
        spans.add(TextSpan(
          text: text.substring(cursor, pos),
          style: activeTypes.isEmpty
              ? null
              : TextStyle(backgroundColor: markColors[activeTypes.last]),
        ));
        cursor = pos;
      }
      if (event.isStart) {
        activeTypes.add(event.type);
      } else {
        activeTypes.remove(event.type);
      }
    }
    if (cursor < length) {
      spans.add(TextSpan(text: text.substring(cursor)));
    }
    return spans;
  }
}
