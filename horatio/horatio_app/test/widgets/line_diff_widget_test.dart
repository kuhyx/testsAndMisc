import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/line_diff_widget.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  group('LineDiffWidget', () {
    testWidgets('renders match, extra, and missing segments', (tester) async {
      const segments = [
        DiffSegment(text: 'the', type: DiffType.match),
        DiffSegment(text: 'cat', type: DiffType.missing),
        DiffSegment(text: 'dog', type: DiffType.extra),
      ];

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: LineDiffWidget(segments: segments),
          ),
        ),
      );

      // The RichText widget should contain all segment texts.
      final richText = tester.widget<RichText>(find.byType(RichText));
      final textSpan = richText.text as TextSpan;
      expect(textSpan.children, hasLength(3));

      // Verify first child is match (no background).
      final matchSpan = textSpan.children![0] as TextSpan;
      expect(matchSpan.text, 'the ');
      expect(matchSpan.style?.backgroundColor, isNull);

      // Extra segment has background.
      final extraSpan = textSpan.children![2] as TextSpan;
      expect(extraSpan.text, 'dog ');
      expect(extraSpan.style?.decoration, TextDecoration.lineThrough);

      // Missing segment has background.
      final missingSpan = textSpan.children![1] as TextSpan;
      expect(missingSpan.text, 'cat ');
      expect(missingSpan.style?.decoration, TextDecoration.underline);
    });
  });
}
