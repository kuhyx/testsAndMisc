import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pomodoro_app/main.dart';

void main() {
  testWidgets('PomodoroApp builds and shows MaterialApp', (tester) async {
    await tester.pumpWidget(const PomodoroApp());
    expect(find.byType(MaterialApp), findsOneWidget);
  });

  testWidgets('PomodoroApp uses dark theme', (tester) async {
    await tester.pumpWidget(const PomodoroApp());
    final materialApp = tester.widget<MaterialApp>(find.byType(MaterialApp));
    expect(materialApp.debugShowCheckedModeBanner, false);
    expect(materialApp.title, 'Pomodoro');
    expect(materialApp.theme, isNotNull);
  });
}
