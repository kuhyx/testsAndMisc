import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/script_card_widget.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  group('ScriptCardWidget', () {
    late Script script;

    setUp(() {
      script = TextParser().parse(
        title: 'Hamlet',
        content: 'HAMLET: To be.\nHORATIO: Indeed.\nHAMLET: Well then.',
      );
    });

    testWidgets('displays script information', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ScriptCardWidget(
              script: script,
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.text('Hamlet'), findsOneWidget);
      expect(find.byIcon(Icons.theater_comedy), findsOneWidget);
      // Shows roles · scenes · lines summary.
      expect(find.textContaining('2 roles'), findsOneWidget);
      // No onDelete means chevron_right icon.
      expect(find.byIcon(Icons.chevron_right), findsOneWidget);
    });

    testWidgets('shows delete button when onDelete is provided',
        (tester) async {
      var deleted = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ScriptCardWidget(
              script: script,
              onTap: () {},
              onDelete: () => deleted = true,
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.delete_outline), findsOneWidget);
      await tester.tap(find.byIcon(Icons.delete_outline));
      expect(deleted, isTrue);
    });

    testWidgets('calls onTap when card is tapped', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ScriptCardWidget(
              script: script,
              onTap: () => tapped = true,
            ),
          ),
        ),
      );

      await tester.tap(find.byType(ListTile));
      expect(tapped, isTrue);
    });
  });
}
