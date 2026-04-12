import 'package:flutter/material.dart';

import 'package:pomodoro_app/screens/pomodoro_screen.dart';
import 'package:pomodoro_app/theme/pomodoro_theme.dart';

void main() {
  runApp(const PomodoroApp());
}

/// The root widget of the Pomodoro application.
class PomodoroApp extends StatelessWidget {
  /// Creates a [PomodoroApp].
  const PomodoroApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
      title: 'Pomodoro',
      debugShowCheckedModeBanner: false,
      theme: PomodoroTheme.darkTheme,
      home: const PomodoroScreen(),
    );
}
