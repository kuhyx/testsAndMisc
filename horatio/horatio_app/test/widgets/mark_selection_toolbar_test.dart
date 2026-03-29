import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/mark_selection_toolbar.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  group('MarkSelectionToolbar', () {
    testWidgets('shows 6 mark type chips', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MarkSelectionToolbar(
              onMarkSelected: (_) {},
              onCancelled: () {},
            ),
          ),
        ),
      );
      expect(find.byType(ActionChip), findsNWidgets(6));
      expect(find.text('Stress'), findsOneWidget);
      expect(find.text('Pause'), findsOneWidget);
      expect(find.text('Breath'), findsOneWidget);
      expect(find.text('Emphasis'), findsOneWidget);
      expect(find.text('Slow Down'), findsOneWidget);
      expect(find.text('Speed Up'), findsOneWidget);
    });

    testWidgets('tapping chip calls onMarkSelected', (tester) async {
      MarkType? selected;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MarkSelectionToolbar(
              onMarkSelected: (type) => selected = type,
              onCancelled: () {},
            ),
          ),
        ),
      );
      await tester.tap(find.text('Stress'));
      expect(selected, MarkType.stress);
    });

    testWidgets('cancel button calls onCancelled', (tester) async {
      var cancelled = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MarkSelectionToolbar(
              onMarkSelected: (_) {},
              onCancelled: () => cancelled = true,
            ),
          ),
        ),
      );
      await tester.ensureVisible(find.text('Cancel'));
      await tester.tap(find.text('Cancel'));
      expect(cancelled, isTrue);
    });
  });
}
