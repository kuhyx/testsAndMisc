import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/mark_type_picker.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  group('MarkTypePicker', () {
    testWidgets('displays all 6 MarkType labels', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MarkTypePicker(onSelected: (_) {}, onCancelled: () {}),
          ),
        ),
      );

      for (final type in MarkType.values) {
        expect(find.text(markTypeLabel(type)), findsOneWidget);
      }
    });

    testWidgets('tapping each type calls onSelected', (tester) async {
      for (final type in MarkType.values) {
        MarkType? selected;

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: MarkTypePicker(
                onSelected: (t) => selected = t,
                onCancelled: () {},
              ),
            ),
          ),
        );

        await tester.tap(find.text(markTypeLabel(type)));
        expect(selected, type);
      }
    });

    testWidgets('tapping cancel calls onCancelled', (tester) async {
      var cancelled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MarkTypePicker(
              onSelected: (_) {},
              onCancelled: () => cancelled = true,
            ),
          ),
        ),
      );

      await tester.tap(find.text('Cancel'));
      expect(cancelled, isTrue);
    });
  });
}
