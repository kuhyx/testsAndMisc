import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:horatio_app/widgets/grade_stars.dart';

void main() {
  group('GradeStars', () {
    testWidgets('shows 5 star icons and blackout button', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: null, onGrade: (_) {}),
          ),
        ),
      );
      expect(find.byIcon(Icons.star_border), findsNWidgets(5));
      expect(find.text('Blackout'), findsOneWidget);
    });

    testWidgets('filled stars match grade', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: 3, onGrade: (_) {}),
          ),
        ),
      );
      expect(find.byIcon(Icons.star), findsNWidgets(3));
      expect(find.byIcon(Icons.star_border), findsNWidgets(2));
    });

    testWidgets('tapping star calls onGrade', (tester) async {
      int? graded;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: null, onGrade: (g) => graded = g),
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.star_border).at(3));

      expect(graded, 4);
    });

    testWidgets('tapping blackout calls onGrade with 0', (tester) async {
      int? graded;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: null, onGrade: (g) => graded = g),
          ),
        ),
      );

      await tester.tap(find.text('Blackout'));

      expect(graded, 0);
    });

    testWidgets('grade 0 highlights blackout button', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: 0, onGrade: (_) {}),
          ),
        ),
      );

      expect(find.byIcon(Icons.star_border), findsNWidgets(5));
    });

    testWidgets('grade 5 fills all stars', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: GradeStars(grade: 5, onGrade: (_) {}),
          ),
        ),
      );

      expect(find.byIcon(Icons.star), findsNWidgets(5));
      expect(find.byIcon(Icons.star_border), findsNothing);
    });
  });
}
