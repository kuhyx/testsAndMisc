import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/grade_badge.dart';
import 'package:horatio_core/horatio_core.dart';

void main() {
  group('GradeBadge', () {
    for (final (grade, label, icon) in [
      (LineMatchGrade.exact, 'Perfect!', Icons.check_circle),
      (LineMatchGrade.minor, 'Close', Icons.info_outline),
      (LineMatchGrade.major, 'Needs Work', Icons.warning),
      (LineMatchGrade.missed, 'Missed', Icons.cancel),
    ]) {
      testWidgets('renders $grade correctly', (tester) async {
        await tester.pumpWidget(
          MaterialApp(home: Scaffold(body: GradeBadge(grade: grade))),
        );
        expect(find.text(label), findsOneWidget);
        expect(find.byIcon(icon), findsOneWidget);
      });
    }
  });
}
