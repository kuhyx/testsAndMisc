import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/mark_overlay.dart';
import 'package:horatio_core/horatio_core.dart';

TextMark _mark({
  required int start,
  required int end,
  MarkType type = MarkType.stress,
}) =>
    TextMark(
      id: 'mark-$start-$end-${type.name}',
      lineIndex: 0,
      startOffset: start,
      endOffset: end,
      type: type,
      createdAt: DateTime(2025),
    );

void main() {
  group('MarkOverlay', () {
    testWidgets('empty marks list renders plain text', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: MarkOverlay(text: 'Hello world', marks: [])),
        ),
      );

      final richText = tester.widget<RichText>(find.byType(RichText));
      final span = richText.text as TextSpan;
      expect(span.text, 'Hello world');
      expect(span.children, isNull);
    });

    testWidgets('single mark renders colored span', (tester) async {
      final marks = [_mark(start: 0, end: 5)];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: MarkOverlay(text: 'Hello world', marks: marks)),
        ),
      );

      final richText = tester.widget<RichText>(find.byType(RichText));
      final span = richText.text as TextSpan;
      expect(span.children, isNotNull);

      final marked = span.children!.first as TextSpan;
      expect(marked.text, 'Hello');
      expect(marked.style?.backgroundColor, markColors[MarkType.stress]);

      final plain = span.children![1] as TextSpan;
      expect(plain.text, ' world');
      expect(plain.style?.backgroundColor, isNull);
    });

    testWidgets('multiple non-overlapping marks', (tester) async {
      final marks = [
        _mark(start: 0, end: 5),
        _mark(start: 6, end: 11, type: MarkType.pause),
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: MarkOverlay(text: 'Hello world', marks: marks)),
        ),
      );

      final richText = tester.widget<RichText>(find.byType(RichText));
      final span = richText.text as TextSpan;
      expect(span.children, hasLength(3));

      final first = span.children![0] as TextSpan;
      expect(first.text, 'Hello');
      expect(first.style?.backgroundColor, markColors[MarkType.stress]);

      final gap = span.children![1] as TextSpan;
      expect(gap.text, ' ');

      final second = span.children![2] as TextSpan;
      expect(second.text, 'world');
      expect(second.style?.backgroundColor, markColors[MarkType.pause]);
    });

    testWidgets('each MarkType maps to distinct color', (tester) async {
      final colors = <Color>{};
      for (final type in MarkType.values) {
        final color = markColors[type];
        expect(color, isNotNull, reason: '$type should have a mapped color');
        colors.add(color!);
      }
      expect(colors, hasLength(MarkType.values.length));
    });

    testWidgets('mark outside text bounds is clamped gracefully',
        (tester) async {
      final marks = [_mark(start: 50, end: 100)];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: MarkOverlay(text: 'Short', marks: marks)),
        ),
      );

      // Should not crash — renders plain text since mark is fully clamped.
      final richText = tester.widget<RichText>(find.byType(RichText));
      expect(richText.text, isA<TextSpan>());
      // When mark start >= end after clamping, it's skipped → children path.
      // The text is still fully rendered either way.
      expect(tester.takeException(), isNull);
    });

    testWidgets('custom style is applied', (tester) async {
      const customStyle = TextStyle(fontSize: 24);

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MarkOverlay(text: 'Styled', marks: [], style: customStyle),
          ),
        ),
      );

      final richText = tester.widget<RichText>(find.byType(RichText));
      final span = richText.text as TextSpan;
      expect(span.style?.fontSize, 24);
    });
  });
}
